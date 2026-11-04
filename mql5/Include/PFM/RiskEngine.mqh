//+------------------------------------------------------------------+
//| PFM RiskEngine.mqh — shared risk engine for every PFM Expert Advisor
//| Mirror of pfm/risk.py. Any failed or errored check REJECTS the order.
//| Inputs are set from the release .set file generated from config/risk/*.yaml.
//+------------------------------------------------------------------+
#ifndef PFM_RISK_ENGINE_MQH
#define PFM_RISK_ENGINE_MQH

#include <Trade/Trade.mqh>

input group "=== PFM risk engine ==="
input double InpAccountSize        = 50000;  // initial balance of the challenge
input double InpRiskPerTradePct    = 0.5;
input double InpThrottleDDPct      = 3.0;
input double InpThrottleRiskPct    = 0.25;
input double InpDailyStopPct       = 1.5;
input double InpKillDDPct          = 6.0;
input double InpDailyProfitStopPct = 1.5;
input double InpMaxDayShareOfTarget= 0.40;
input double InpStepTargetPct      = 10.0;   // current challenge step target (10 step 1, 5 step 2, 0 funded)
input int    InpMaxOpenPositions   = 2;
input double InpMaxOpenRiskPct     = 1.0;
input int    InpMaxTradesPerDay    = 3;
input string InpEntryStartIST      = "13:30";
input string InpEntryEndIST        = "21:00";
input string InpFlatByIST          = "22:30";
input int    InpNewsFlatBeforeMin  = 10;
input int    InpNewsResumeAfterMin = 15;
input int    InpMinHoldSeconds     = 120;
input double InpSpreadMaxRatio     = 1.5;
input int    InpStaleFeedSeconds   = 30;
input long   InpMagic              = 1010;
input string InpKillFlagFile       = "PFM_KILL.flag"; // in MQL5/Files (Common); monitor creates it
input bool   InpUseNewsFilter      = true;   // calendar is unavailable in the Strategy Tester; filter is skipped there
input bool   InpMaxLossTrailing    = true;   // firm max_loss_trailing: kill and throttle follow the EOD high-water mark

#define IST_OFFSET_SEC 19800   // UTC+5:30, India has no DST

//--- PFM-LIMITS-BEGIN pure arithmetic, no MT5 calls; tests/test_trailing.py compiles this block and compares it with pfm/risk.py
double PfmMark(bool trailing,double size,double eodHwm)        { return (trailing && eodHwm>size) ? eodHwm : size; }
double PfmDrawdownPct(double mark,double size,double eq)       { return (mark-eq)/size*100.0; }
double PfmKillRoom(double mark,double size,double killPct,double eq,double openRisk)
                                                               { return size*killPct/100.0-(mark-eq)-openRisk; }
double PfmDayBase(double dayStart,double dayPeak)              { return (dayPeak>dayStart) ? dayPeak : dayStart; }
//--- PFM-LIMITS-END

class CRiskEngine
  {
private:
   CTrade   m_trade;
   double   m_dayStartEquity;
   double   m_dayPeakEquity;
   double   m_eodHwm;         // highest day-roll equity so far; kept in a terminal global variable across restarts
   int      m_dayKey;
   int      m_tradesToday;
   bool     m_lockedForDay;
   bool     m_killed;
   double   m_spreadHist[];   // recent spreads in points for the median

   int      ToMinutes(string hhmm) { string p[]; if(StringSplit(hhmm,':',p)!=2) return -1; return (int)StringToInteger(p[0])*60+(int)StringToInteger(p[1]); }
   datetime IstNow()    { return TimeGMT()+IST_OFFSET_SEC; }
   int      IstMinutes(){ MqlDateTime t; TimeToStruct(IstNow(),t); return t.hour*60+t.min; }
   int      IstDow()    { MqlDateTime t; TimeToStruct(IstNow(),t); return t.day_of_week; }
   int      IstDayKey() { MqlDateTime t; TimeToStruct(IstNow(),t); return t.year*1000+t.day_of_year; }

   string   HwmKey() { return "PFM_HWM_"+IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)); }
   double   Mark()   { return PfmMark(InpMaxLossTrailing,InpAccountSize,m_eodHwm); }

   void     LoadHwm()
     {
      m_eodHwm=InpAccountSize;
      if(GlobalVariableCheck(HwmKey())) m_eodHwm=MathMax(m_eodHwm,GlobalVariableGet(HwmKey()));
     }
   //--- a restart also counts as a roll: intraday equity can only raise the mark, which tightens
   void     SaveHwm(double value)
     {
      m_eodHwm=MathMax(m_eodHwm,value);
      if(GlobalVariableSet(HwmKey(),m_eodHwm)==0) PrintFormat("PFM HWM not saved: %d",GetLastError());
      GlobalVariablesFlush();
     }

   double   OpenRiskUsd()
     {
      double risk=0;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         ulong tk=PositionGetTicket(i);
         if(!PositionSelectByTicket(tk) || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
         double sl=PositionGetDouble(POSITION_SL), op=PositionGetDouble(POSITION_PRICE_OPEN), vol=PositionGetDouble(POSITION_VOLUME);
         if(sl<=0) { risk+=1e9; continue; }          // a position without SL counts as unlimited risk
         risk+=MathAbs(op-sl)*vol*ValuePerPriceUnit();
        }
      return risk;
     }
   int      OpenCount()
     {
      int n=0;
      for(int i=PositionsTotal()-1;i>=0;i--){ ulong tk=PositionGetTicket(i); if(PositionSelectByTicket(tk) && PositionGetInteger(POSITION_MAGIC)==InpMagic) n++; }
      return n;
     }
   double   SpreadMedian()
     {
      int n=ArraySize(m_spreadHist); if(n<50) return 0;
      double c[]; ArrayCopy(c,m_spreadHist); ArraySort(c); return c[n/2];
     }

public:
   void     Init()
     {
      m_trade.SetExpertMagicNumber(InpMagic);
      m_trade.SetDeviationInPoints(30);
      m_dayKey=-1; m_killed=false;
      LoadHwm();
      RollDay();
      Print("PFM risk engine ready | size=",InpAccountSize," risk=",InpRiskPerTradePct,"% daily stop=",InpDailyStopPct,"% kill=",InpKillDDPct,
            "% trailing=",InpMaxLossTrailing," mark=",DoubleToString(Mark(),2));
     }
   CTrade*  Trade()     { return &m_trade; }
   bool     Killed()    { return m_killed; }

   double   ValuePerPriceUnit()   // account currency per 1.0 price move per 1 lot
     {
      double tv=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE), ts=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);
      return (ts>0)? tv/ts : 0;
     }

   void     RollDay()
     {
      int k=IstDayKey();
      if(k!=m_dayKey)
        {
         m_dayKey=k;
         m_dayStartEquity=MathMax(AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_BALANCE));
         m_dayPeakEquity=m_dayStartEquity;
         m_tradesToday=0; m_lockedForDay=false;
         SaveHwm(m_dayStartEquity);       // also touches the variable daily, so the terminal's 4-week expiry never hits it
        }
     }

   void     RecordSpread()
     {
      int n=ArraySize(m_spreadHist);
      if(n>=2000) { ArrayRemove(m_spreadHist,0,1); n--; }
      ArrayResize(m_spreadHist,n+1); m_spreadHist[n]=(double)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD);
     }

   bool     KillFlagPresent() { return FileIsExist(InpKillFlagFile,FILE_COMMON); }

   //--- call on every tick. Flattens and locks when a limit is hit. Returns false if trading is stopped.
   bool     OnTickLimits(bool newsBlackoutNow)
     {
      RollDay();
      double eq=AccountInfoDouble(ACCOUNT_EQUITY);
      double ddPct=PfmDrawdownPct(Mark(),InpAccountSize,eq);
      m_dayPeakEquity=MathMax(m_dayPeakEquity,eq);
      if(KillFlagPresent() || ddPct>=InpKillDDPct)
        { if(!m_killed) Print("PFM KILL: dd=",DoubleToString(ddPct,2),"% flag=",KillFlagPresent()); m_killed=true; FlattenAll("kill"); return false; }
      if((PfmDayBase(m_dayStartEquity,m_dayPeakEquity)-eq)/InpAccountSize*100.0>=InpDailyStopPct)
        { if(!m_lockedForDay) Print("PFM daily stop"); m_lockedForDay=true; FlattenAll("daily_stop"); return false; }
      if((eq-m_dayStartEquity)/InpAccountSize*100.0>=InpDailyProfitStopPct)
        { if(!m_lockedForDay) Print("PFM daily profit stop"); m_lockedForDay=true; FlattenAll("daily_profit_stop"); return false; }
      if(InpStepTargetPct>0 && (eq-m_dayStartEquity)>=InpMaxDayShareOfTarget*InpAccountSize*InpStepTargetPct/100.0)
        { m_lockedForDay=true; FlattenAll("day_share_cap"); return false; }
      int m=IstMinutes(), dow=IstDow();
      if(m>=ToMinutes(InpFlatByIST) || dow==0 || dow==6) FlattenAll("session_end");
      if(newsBlackoutNow) FlattenAll("news");
      return !m_lockedForDay;
     }

   void     FlattenAll(string why)
     {
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         ulong tk=PositionGetTicket(i);
         if(!PositionSelectByTicket(tk) || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
         if(TimeCurrent()-(datetime)PositionGetInteger(POSITION_TIME)<InpMinHoldSeconds && why!="kill" && why!="daily_stop") continue;
         if(!m_trade.PositionClose(tk)) PrintFormat("PFM close failed %I64u (%s): %d",tk,why,GetLastError());
        }
     }

   //--- per-order gate. Returns lots (>0) or 0 with a reason. Never throws: any doubt = reject.
   double   Check(double entry,double stop,bool newsBlackoutNow,string &reason)
     {
      RollDay();
      if(m_killed)            { reason="killed"; return 0; }
      if(m_lockedForDay)      { reason="locked_for_day"; return 0; }
      if(stop<=0)             { reason="no_stop"; return 0; }
      if(TimeCurrent()-(datetime)SymbolInfoInteger(_Symbol,SYMBOL_TIME)>InpStaleFeedSeconds) { reason="stale_feed"; return 0; }
      int m=IstMinutes(), dow=IstDow();
      if(dow==0 || dow==6 || m<ToMinutes(InpEntryStartIST) || m>=ToMinutes(InpEntryEndIST)) { reason="outside_hours"; return 0; }
      if(newsBlackoutNow)     { reason="news_blackout"; return 0; }
      if(m_tradesToday>=InpMaxTradesPerDay) { reason="max_trades"; return 0; }
      if(OpenCount()>=InpMaxOpenPositions)  { reason="max_positions"; return 0; }
      double med=SpreadMedian(), sp=(double)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD);
      if(med>0 && sp>InpSpreadMaxRatio*med) { reason="spread"; return 0; }
      double eq=AccountInfoDouble(ACCOUNT_EQUITY);
      double dd=PfmDrawdownPct(Mark(),InpAccountSize,eq);
      double riskUsd=InpAccountSize*((dd>=InpThrottleDDPct)?InpThrottleRiskPct:InpRiskPerTradePct)/100.0;
      double openRisk=OpenRiskUsd();
      if(openRisk+riskUsd>InpAccountSize*InpMaxOpenRiskPct/100.0+1e-9) { reason="max_open_risk"; return 0; }
      double dayRoom =InpAccountSize*InpDailyStopPct/100.0-(m_dayStartEquity-eq)-openRisk;
      double killRoom=PfmKillRoom(Mark(),InpAccountSize,InpKillDDPct,eq,openRisk);
      riskUsd=MathMin(riskUsd,MathMin(dayRoom,killRoom));
      double vpu=ValuePerPriceUnit(), dist=MathAbs(entry-stop);
      if(vpu<=0 || dist<=0 || riskUsd<=0) { reason="size_zero"; return 0; }
      double step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP), vmin=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN), vmax=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX);
      double lots=MathFloor(riskUsd/(dist*vpu)/step+1e-9)*step;
      if(lots<vmin) { reason="size_zero"; return 0; }
      lots=MathMin(lots,vmax);
      reason="ok";
      return NormalizeDouble(lots,2);
     }

   bool     Open(int dir,double lots,double stop,double target,string comment)
     {
      bool ok = (dir>0) ? m_trade.Buy(lots,_Symbol,0,stop,target,comment)
                        : m_trade.Sell(lots,_Symbol,0,stop,target,comment);
      if(ok) m_tradesToday++;
      else PrintFormat("PFM order failed: %d %s",m_trade.ResultRetcode(),m_trade.ResultRetcodeDescription());
      return ok;
     }
  };

//--- News blackout from the MT5 economic calendar (USD, high importance)
bool PfmNewsBlackout()
  {
   if(!InpUseNewsFilter || MQLInfoInteger(MQL_TESTER)) return false;
   datetime now=TimeTradeServer();
   MqlCalendarValue vals[];
   datetime from=now-InpNewsResumeAfterMin*60, to=now+InpNewsFlatBeforeMin*60;
   ResetLastError();
   if(!CalendarValueHistory(vals,from,to,NULL,"USD")) return true;   // calendar error → fail-safe: treat as blackout
   for(int i=0;i<ArraySize(vals);i++)
     {
      MqlCalendarEvent ev;
      if(CalendarEventById(vals[i].event_id,ev) && ev.importance==CALENDAR_IMPORTANCE_HIGH) return true;
     }
   return false;
  }

#endif
