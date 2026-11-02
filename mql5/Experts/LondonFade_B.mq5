//+------------------------------------------------------------------+
//| LondonFade_B.mq5 — Strategy B: Asian-range false-breakout fade (H-002)
//| Mirror of strategies/B_london_fade/strategy.py. XAUUSD, M15 chart.
//| Same range/session/stop code path as GoldBreakout_A.mq5; only the entry side flips.
//| All orders go through CRiskEngine (PFM/RiskEngine.mqh).
//|
//| Minimum hold (The5ers min_trade_seconds 60; risk engine InpMinHoldSeconds 120):
//|  - The stop-loss is attached WITH the order (visible SL, hard rule 7).
//|  - The take-profit is NOT attached at entry. It is added only once the position is at least
//|    InpMinHoldSeconds old, so no intrabar TP can close the trade inside the minimum hold.
//|    If price is already through the target at that moment, the EA closes at market (rule-based close,
//|    after the minimum hold).
//|  - The EA itself never closes by rule inside InpMinHoldSeconds (FlattenAll in the risk engine skips
//|    young positions except kill / daily_stop).
//|  - A broker-side SL hit inside 60 s cannot be blocked without hiding the stop; see Q-002 item 2.
//+------------------------------------------------------------------+
#property copyright "Prop Firm Manager"
#property version   "1.00"
#property strict

#include <PFM/RiskEngine.mqh>

input group "=== Strategy B ==="
input double InpRR          = 2.0;
input double InpStopATR     = 1.2;
input double InpMinRangeATR = 1.5;
input double InpMaxRangeATR = 4.0;
input string InpRangeStart  = "05:30";  // IST
input string InpRangeEnd    = "12:30";  // IST
input string InpTradeStart  = "13:30";  // IST, first M15 close considered is after this
input string InpTradeEnd    = "16:30";  // IST
input string InpStatusFile  = "PFM_status_B.json"; // heartbeat for pfm/monitor.py (Common files)

CRiskEngine Risk;
int         hATR;
int         lastSignalDay=-1;
datetime    lastBar=0;

int Min(string s){ string p[]; StringSplit(s,':',p); return (int)StringToInteger(p[0])*60+(int)StringToInteger(p[1]); }
int IstMin(datetime gmt){ MqlDateTime t; TimeToStruct(gmt+IST_OFFSET_SEC,t); return t.hour*60+t.min; }
int IstDay(datetime gmt){ MqlDateTime t; TimeToStruct(gmt+IST_OFFSET_SEC,t); return t.year*1000+t.day_of_year; }
string TpKey(ulong ticket){ return "PFM_B_TP_"+(string)ticket; }   // pending target survives an EA restart

int OnInit()
  {
   if(_Period!=PERIOD_M15) { Print("Attach to an M15 chart"); return INIT_PARAMETERS_INCORRECT; }
   hATR=iATR(_Symbol,PERIOD_H1,14);
   if(hATR==INVALID_HANDLE) return INIT_FAILED;
   Risk.Init();
   EventSetTimer(60);
   return INIT_SUCCEEDED;
  }
void OnDeinit(const int r){ EventKillTimer(); IndicatorRelease(hATR); }

void WriteStatus()
  {
   int h=FileOpen(InpStatusFile,FILE_WRITE|FILE_TXT|FILE_COMMON|FILE_ANSI);
   if(h==INVALID_HANDLE) return;
   FileWriteString(h,StringFormat("{\"ea\":\"LondonFade_B\",\"version\":\"1.00\",\"time_gmt\":\"%s\",\"equity\":%.2f,\"balance\":%.2f,\"positions\":%d,\"killed\":%s}",
      TimeToString(TimeGMT(),TIME_DATE|TIME_SECONDS),AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_BALANCE),
      PositionsTotal(),Risk.Killed()?"true":"false"));
   FileClose(h);
  }
void OnTimer(){ WriteStatus(); }

//--- attach the deferred take-profit once the position has passed the minimum hold
void ManageDeferredTargets()
  {
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i);
      if(!PositionSelectByTicket(tk) || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      string key=TpKey(tk);
      if(!GlobalVariableCheck(key)) continue;
      if(TimeCurrent()-(datetime)PositionGetInteger(POSITION_TIME)<InpMinHoldSeconds) continue;
      double tp=GlobalVariableGet(key), sl=PositionGetDouble(POSITION_SL);
      long   type=PositionGetInteger(POSITION_TYPE);
      double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID), ask=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
      bool through=(type==POSITION_TYPE_BUY)? (bid>=tp) : (ask<=tp);
      bool ok = through ? Risk.Trade().PositionClose(tk) : Risk.Trade().PositionModify(tk,sl,tp);
      if(ok) GlobalVariableDel(key);
      else PrintFormat("PFM-B deferred TP failed %I64u: %d",tk,GetLastError());
     }
  }

void OnTick()
  {
   Risk.RecordSpread();
   bool news=PfmNewsBlackout();
   bool canTrade=Risk.OnTickLimits(news);
   ManageDeferredTargets();
   if(!canTrade) return;

   datetime bar=iTime(_Symbol,PERIOD_M15,0);
   if(bar==lastBar) return;          // act once per new M15 bar, on the bar that just closed
   lastBar=bar;

   datetime closeTimeServer=bar;     // bar index 1 = just closed; its close time = bar(0) open time
   datetime closeGmt=closeTimeServer-(TimeTradeServer()-TimeGMT());
   int cm=IstMin(closeGmt), day=IstDay(closeGmt);
   if(day==lastSignalDay) return;
   if(cm<=Min(InpTradeStart) || cm>Min(InpTradeEnd)) return;

   // Asian range from today's M15 bars whose IST open in [RangeStart, RangeEnd) — identical to A
   double hi=-DBL_MAX, lo=DBL_MAX; int n=0;
   for(int i=1;i<=60;i++)
     {
      datetime t=iTime(_Symbol,PERIOD_M15,i);
      datetime g=t-(TimeTradeServer()-TimeGMT());
      if(IstDay(g)!=day) break;
      int om=IstMin(g);
      if(om>=Min(InpRangeStart) && om+15<=Min(InpRangeEnd))
        { hi=MathMax(hi,iHigh(_Symbol,PERIOD_M15,i)); lo=MathMin(lo,iLow(_Symbol,PERIOD_M15,i)); n++; }
     }
   if(n<8) return;
   double atr[1]; if(CopyBuffer(hATR,0,1,1,atr)!=1 || atr[0]<=0) return;
   double width=hi-lo;
   if(width<InpMinRangeATR*atr[0] || width>InpMaxRangeATR*atr[0]) { lastSignalDay=day; return; }

   double c=iClose(_Symbol,PERIOD_M15,1);
   int brk = (c>hi)? 1 : (c<lo)? -1 : 0;
   if(brk==0) return;
   double mid=(hi+lo)/2.0;
   double atrStop=c-brk*InpStopATR*atr[0];
   double aStop=(brk>0)? MathMax(mid,atrStop) : MathMin(mid,atrStop);   // A's stop (tighter of the two)
   double risk=MathAbs(c-aStop);
   lastSignalDay=day;                 // one attempt per day, taken or rejected
   if(risk<=0) return;

   int dir=-brk;                      // FADE: opposite side to the break
   double stop=c-dir*risk;            // on the breakout side, same distance as A
   double entry=(dir>0)? SymbolInfoDouble(_Symbol,SYMBOL_ASK) : SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if((dir>0 && stop>=entry) || (dir<0 && stop<=entry)) return;
   double target=entry+dir*InpRR*MathAbs(entry-stop);
   stop=NormalizeDouble(stop,_Digits); target=NormalizeDouble(target,_Digits);

   string why;
   double lots=Risk.Check(entry,stop,news,why);
   if(lots<=0) { Print("PFM rejected: ",why); return; }
   if(Risk.Open(dir,lots,stop,0.0,"PFM-B"))          // SL now, TP deferred past the minimum hold
     {
      ulong tk=0;
      // find the new position (netting or hedging account) by magic + newest open time
      datetime newest=0;
      for(int i=PositionsTotal()-1;i>=0;i--)
        {
         ulong t=PositionGetTicket(i);
         if(!PositionSelectByTicket(t) || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
         datetime ot=(datetime)PositionGetInteger(POSITION_TIME);
         if(ot>=newest && PositionGetDouble(POSITION_TP)==0) { newest=ot; tk=t; }
        }
      if(tk>0) GlobalVariableSet(TpKey(tk),target);
      else Print("PFM-B: could not find new position to defer TP; position has SL only");
     }
  }
