//+------------------------------------------------------------------+
//| UsOpenImpulse_E.mq5 — Strategy E: US-open impulse continuation (H-004)
//| Mirror of strategies/E_us_open_impulse/strategy.py. XAUUSD, M15 chart.
//| All orders go through CRiskEngine (PFM/RiskEngine.mqh).
//|
//| All strategy times are New York. MQL5 has no time zone database, so NyOffset() computes the US DST rule.
//| Rules:
//|  I = (close of the 09:15 ET M15 bar − open of the 08:30 ET M15 bar) / H1 ATR(14) from the last H1 bar closed
//|  at or before 09:30 ET. If |I| >= InpImpulseATR: trade in the direction of I at the 09:30 ET bar open
//|  (19:00 or 20:00 IST). SL = signal close ∓ InpStopATR × ATR at entry, no TP, close at InpExitET (after the
//|  risk engine's minimum hold). One attempt a day, Mon–Fri.
//|
//| NOTE (H-004 "known problem"): OnTickLimits flattens for every USD high-importance event in the MT5 calendar.
//| The backtest calendar holds FOMC, NFP and CPI only, so a 10:00 ET release rated high would close the trade
//| here at 09:50 ET but not in the backtest. Required check before demo.
//| The Python benchmark switches (random_side | opposite_side | no_filter) are research-only and not in this EA.
//+------------------------------------------------------------------+
#property copyright "Prop Firm Manager"
#property version   "1.00"
#property strict

#include <PFM/RiskEngine.mqh>

input group "=== Strategy E ==="
input double InpImpulseATR = 1.0;
input double InpStopATR    = 1.5;
input string InpExitET     = "11:30";  // 10:30, 11:00 or 11:30 New York
input string InpStatusFile = "PFM_status_E.json"; // heartbeat for pfm/monitor.py (Common files)

#define ENTRY_MIN_ET 570      // 09:30 New York
#define IMPULSE_SECS 3600     // 08:30 bar open is one hour before the 09:30 bar open

CRiskEngine Risk;
int         hATR;
int         lastSignalDay=-1;
datetime    lastBar=0;

int Min(string s){ string p[]; StringSplit(s,':',p); return (int)StringToInteger(p[0])*60+(int)StringToInteger(p[1]); }
//--- rounded to 15 min: a one-second clock difference must not move the bar off 09:30 ET and lose the day's entry
long SrvOffset(){ return (long)MathRound((double)(TimeTradeServer()-TimeGMT())/900.0)*900; }

//--- PFM-DST-BEGIN (tests/test_strategy_e.py compiles this block and checks it against the tz database)
//--- UTC instant of 00:00 on the first Sunday on or after <year>-<month>-<dayFrom>
datetime SundayOnOrAfter(int year,int month,int dayFrom)
  {
   MqlDateTime t;
   ZeroMemory(t);
   t.year=year; t.mon=month; t.day=dayFrom;
   datetime d=StructToTime(t);
   TimeToStruct(d,t);
   return d+(datetime)(((7-t.day_of_week)%7)*86400);
  }
//--- New York UTC offset in seconds at a GMT instant. US rule since 2007: daylight time starts on the second
//--- Sunday of March at 02:00 EST (07:00 UTC) and ends on the first Sunday of November at 02:00 EDT (06:00 UTC).
long NyOffset(datetime gmt)
  {
   MqlDateTime t;
   TimeToStruct(gmt,t);
   datetime start=SundayOnOrAfter(t.year,3,8)+7*3600;
   datetime end=SundayOnOrAfter(t.year,11,1)+6*3600;
   return (gmt>=start && gmt<end) ? -4*3600 : -5*3600;
  }
//--- PFM-DST-END

datetime NyLocal(datetime gmt){ return gmt+(datetime)NyOffset(gmt); }
int NyMin(datetime gmt){ MqlDateTime t; TimeToStruct(NyLocal(gmt),t); return t.hour*60+t.min; }
int NyDay(datetime gmt){ return (int)((long)NyLocal(gmt)/86400); }
int NyDow(datetime gmt){ MqlDateTime t; TimeToStruct(NyLocal(gmt),t); return t.day_of_week; }

int OnInit()
  {
   if(_Period!=PERIOD_M15) { Print("Attach to an M15 chart"); return INIT_PARAMETERS_INCORRECT; }
   if(Min(InpExitET)<=ENTRY_MIN_ET) { Print("InpExitET must be after 09:30"); return INIT_PARAMETERS_INCORRECT; }
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
   FileWriteString(h,StringFormat("{\"ea\":\"UsOpenImpulse_E\",\"version\":\"1.00\",\"time_gmt\":\"%s\",\"equity\":%.2f,\"balance\":%.2f,\"positions\":%d,\"killed\":%s}",
      TimeToString(TimeGMT(),TIME_DATE|TIME_SECONDS),AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_BALANCE),
      PositionsTotal(),Risk.Killed()?"true":"false"));
   FileClose(h);
  }
void OnTimer(){ WriteStatus(); CloseAtExitTime(); }

//--- H1 ATR from completed H1 bars as of a given M15 bar open (same alignment as pfm.strategy_base.h1_atr_on)
double AtrAtM15Open(datetime m15OpenServer)
  {
   int sh=iBarShift(_Symbol,PERIOD_H1,m15OpenServer,false);
   if(sh<0) return 0;
   if(iTime(_Symbol,PERIOD_H1,sh)+3600>m15OpenServer) sh++;   // H1 bar not yet closed at this time → use the previous one
   double a[1]; if(CopyBuffer(hATR,0,sh,1,a)!=1) return 0;
   return a[0];
  }

//--- time exit: close at/after InpExitET of the entry's New York day, never inside the minimum hold.
//--- DST changes at 02:00, so the entry's offset is valid for the exit time of the same day.
void CloseAtExitTime()
  {
   datetime nowGmt=TimeGMT();
   for(int i=PositionsTotal()-1;i>=0;i--)
     {
      ulong tk=PositionGetTicket(i);
      if(!PositionSelectByTicket(tk) || PositionGetInteger(POSITION_MAGIC)!=InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      datetime openSrv=(datetime)PositionGetInteger(POSITION_TIME);
      datetime openGmt=openSrv-(datetime)SrvOffset();
      datetime exitGmt=(datetime)((long)NyDay(openGmt)*86400+Min(InpExitET)*60-NyOffset(openGmt));
      if(nowGmt<exitGmt) continue;
      if(TimeCurrent()-openSrv<InpMinHoldSeconds) continue;
      if(!Risk.Trade().PositionClose(tk)) PrintFormat("PFM-E time exit failed %I64u: %d",tk,GetLastError());
     }
  }

void OnTick()
  {
   Risk.RecordSpread();
   bool news=PfmNewsBlackout();
   bool canTrade=Risk.OnTickLimits(news);
   CloseAtExitTime();
   if(!canTrade) return;

   datetime bar=iTime(_Symbol,PERIOD_M15,0);
   if(bar==lastBar) return;          // act once per new M15 bar
   lastBar=bar;

   datetime entryGmt=bar-(datetime)SrvOffset();       // open of bar 0 = close of bar 1
   int day=NyDay(entryGmt), dow=NyDow(entryGmt);
   if(day==lastSignalDay || dow==0 || dow==6) return;
   if(NyMin(entryGmt)!=ENTRY_MIN_ET) return;          // only the 09:30 ET bar open
   lastSignalDay=day;                                 // one attempt per day, taken or rejected

   // both impulse bars must exist, as in the Python version
   if(iTime(_Symbol,PERIOD_M15,1)!=bar-15*60) { Print("PFM-E: no 09:15 ET bar, skip"); return; }
   int first=iBarShift(_Symbol,PERIOD_M15,bar-IMPULSE_SECS,true);
   if(first<0) { Print("PFM-E: no 08:30 ET bar, skip"); return; }

   double a=AtrAtM15Open(bar);
   if(a<=0) return;
   double c=iClose(_Symbol,PERIOD_M15,1);
   double impulse=(c-iOpen(_Symbol,PERIOD_M15,first))/a;
   if(impulse==0 || MathAbs(impulse)<InpImpulseATR) return;

   int dir=impulse>0 ? 1 : -1;
   double stop=NormalizeDouble(c-dir*InpStopATR*a,_Digits);
   double entry=SymbolInfoDouble(_Symbol,dir==1?SYMBOL_ASK:SYMBOL_BID);
   if((dir==1 && stop>=entry) || (dir==-1 && stop<=entry)) return;

   string why;
   double lots=Risk.Check(entry,stop,news,why);
   if(lots<=0) { Print("PFM rejected: ",why); return; }
   Risk.Open(dir,lots,stop,0.0,"PFM-E");              // visible SL, no TP, time exit
  }
