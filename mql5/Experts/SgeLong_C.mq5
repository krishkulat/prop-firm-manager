//+------------------------------------------------------------------+
//| SgeLong_C.mq5 — Strategy C: long gold in the SGE day session after a Western-hours drop (H-003)
//| Mirror of strategies/C_sge_session_long/strategy.py. XAUUSD, M15 chart. Long only.
//| All orders go through CRiskEngine (PFM/RiskEngine.mqh).
//|
//| All strategy times are UTC (China has no DST). Rules:
//|  W = close at 21:00 − close at 13:30 of the previous trading day, in H1 ATR(14) units.
//|  If W <= −InpWestDropATR: buy at the 01:00 UTC bar open, SL = signal close − InpStopATR × H1 ATR,
//|  no TP, close at InpExitUTC (after the risk engine's minimum hold).
//|
//| NOTE (Q-002): the current risk profile entry window is 13:30–21:00 IST. CRiskEngine.Check() rejects a
//| 06:30 IST entry as "outside_hours" until the owner approves an Asian entry window for this EA's .set file.
//| The Python benchmark switches (benchmark: no_filter | random_hour) are research-only and not in this EA.
//+------------------------------------------------------------------+
#property copyright "Prop Firm Manager"
#property version   "1.00"
#property strict

#include <PFM/RiskEngine.mqh>

input group "=== Strategy C ==="
input double InpWestDropATR = 0.5;
input double InpStopATR     = 2.0;
input string InpExitUTC     = "07:30";  // 07:30 (SGE day close) or 09:00
input string InpStatusFile  = "PFM_status_C.json"; // heartbeat for pfm/monitor.py (Common files)

#define ENTRY_MIN_UTC   60      // 01:00 UTC
#define WEST_START_MIN 810      // 13:30 UTC
#define WEST_END_MIN  1260      // 21:00 UTC
#define TOL_MIN         30      // reference close must be within 30 min before the reference time

CRiskEngine Risk;
int         hATR;
int         lastSignalDay=-1;
datetime    lastBar=0;

int Min(string s){ string p[]; StringSplit(s,':',p); return (int)StringToInteger(p[0])*60+(int)StringToInteger(p[1]); }
long SrvOffset(){ return (long)(TimeTradeServer()-TimeGMT()); }
int GmtMin(datetime gmt){ MqlDateTime t; TimeToStruct(gmt,t); return t.hour*60+t.min; }
int GmtDay(datetime gmt){ return (int)(gmt/86400); }
int GmtDow(datetime gmt){ MqlDateTime t; TimeToStruct(gmt,t); return t.day_of_week; }

int OnInit()
  {
   if(_Period!=PERIOD_M15) { Print("Attach to an M15 chart"); return INIT_PARAMETERS_INCORRECT; }
   if(Min(InpExitUTC)<=ENTRY_MIN_UTC) { Print("InpExitUTC must be after 01:00"); return INIT_PARAMETERS_INCORRECT; }
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
   FileWriteString(h,StringFormat("{\"ea\":\"SgeLong_C\",\"version\":\"1.00\",\"time_gmt\":\"%s\",\"equity\":%.2f,\"balance\":%.2f,\"positions\":%d,\"killed\":%s}",
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

//--- time exit: close at/after InpExitUTC of the entry's UTC day, never inside the minimum hold
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
      datetime exitGmt=(datetime)(GmtDay(openGmt)*86400+Min(InpExitUTC)*60);
      if(nowGmt<exitGmt) continue;
      if(TimeCurrent()-openSrv<InpMinHoldSeconds) continue;
      if(!Risk.Trade().PositionClose(tk)) PrintFormat("PFM-C time exit failed %I64u: %d",tk,GetLastError());
     }
  }

//--- Western-hours return of the most recent trading day before `todayGmt`, in ATR units. false if unavailable.
bool WestReturn(int today,double &w)
  {
   long off=SrvOffset();
   double cEnd=0,cStart=0,aEnd=0; int dEnd=-1;
   for(int i=1;i<=500;i++)
     {
      datetime oSrv=iTime(_Symbol,PERIOD_M15,i);
      if(oSrv==0) break;
      datetime cGmt=oSrv+15*60-(datetime)off;          // close time of bar i in GMT
      int d=GmtDay(cGmt), m=GmtMin(cGmt);
      if(d>=today) continue;
      if(dEnd<0)
        {
         if(m<=WEST_END_MIN && m>WEST_END_MIN-TOL_MIN)
           { dEnd=d; cEnd=iClose(_Symbol,PERIOD_M15,i); aEnd=AtrAtM15Open(oSrv); }
         else if(d<today-7) break;
         continue;
        }
      if(d<dEnd) break;                               // start bar must be on the same day as the end bar
      if(m<=WEST_START_MIN && m>WEST_START_MIN-TOL_MIN) { cStart=iClose(_Symbol,PERIOD_M15,i); break; }
     }
   if(dEnd<0 || cStart==0 || aEnd<=0) return false;
   w=(cEnd-cStart)/aEnd;
   return true;
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

   datetime closeGmt=bar-(datetime)SrvOffset();     // close time of bar 1 = open of bar 0
   int day=GmtDay(closeGmt), dow=GmtDow(closeGmt);
   if(day==lastSignalDay || dow==0 || dow==6) return;
   if(GmtMin(closeGmt)!=ENTRY_MIN_UTC) return;        // only the 01:00 UTC bar open
   lastSignalDay=day;                                 // one attempt per day, taken or rejected

   double w;
   if(!WestReturn(day,w)) { Print("PFM-C: no Western-hours reference bars, skip"); return; }
   if(w>-InpWestDropATR) return;

   double c=iClose(_Symbol,PERIOD_M15,1);
   double a=AtrAtM15Open(iTime(_Symbol,PERIOD_M15,1));
   if(a<=0) return;
   double stop=NormalizeDouble(c-InpStopATR*a,_Digits);
   double entry=SymbolInfoDouble(_Symbol,SYMBOL_ASK);
   if(stop>=entry) return;

   string why;
   double lots=Risk.Check(entry,stop,news,why);
   if(lots<=0) { Print("PFM rejected: ",why); return; }
   Risk.Open(1,lots,stop,0.0,"PFM-C");                // visible SL, no TP, time exit
  }
