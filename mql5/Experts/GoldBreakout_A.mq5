//+------------------------------------------------------------------+
//| GoldBreakout_A.mq5 — Strategy A: Asian-range breakout (H-001)
//| Mirror of strategies/A_asian_breakout/strategy.py. XAUUSD, M15 chart.
//| All orders go through CRiskEngine (PFM/RiskEngine.mqh).
//+------------------------------------------------------------------+
#property copyright "Prop Firm Manager"
#property version   "1.00"
#property strict

#include <PFM/RiskEngine.mqh>

input group "=== Strategy A ==="
input double InpRR          = 2.0;
input double InpStopATR     = 1.2;
input double InpMinRangeATR = 0.5;
input double InpMaxRangeATR = 2.0;
input string InpRangeStart  = "05:30";  // IST
input string InpRangeEnd    = "12:30";  // IST
input string InpTradeStart  = "13:30";  // IST, first M15 close considered is after this
input string InpTradeEnd    = "16:30";  // IST
input string InpStatusFile  = "PFM_status_A.json"; // heartbeat for pfm/monitor.py (Common files)

CRiskEngine Risk;
int         hATR;
int         lastSignalDay=-1;
datetime    lastBar=0;

int Min(string s){ string p[]; StringSplit(s,':',p); return (int)StringToInteger(p[0])*60+(int)StringToInteger(p[1]); }
int IstMin(datetime gmt){ MqlDateTime t; TimeToStruct(gmt+IST_OFFSET_SEC,t); return t.hour*60+t.min; }
int IstDay(datetime gmt){ MqlDateTime t; TimeToStruct(gmt+IST_OFFSET_SEC,t); return t.year*1000+t.day_of_year; }

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
   FileWriteString(h,StringFormat("{\"ea\":\"GoldBreakout_A\",\"version\":\"1.00\",\"time_gmt\":\"%s\",\"equity\":%.2f,\"balance\":%.2f,\"positions\":%d,\"killed\":%s}",
      TimeToString(TimeGMT(),TIME_DATE|TIME_SECONDS),AccountInfoDouble(ACCOUNT_EQUITY),AccountInfoDouble(ACCOUNT_BALANCE),
      PositionsTotal(),Risk.Killed()?"true":"false"));
   FileClose(h);
  }
void OnTimer(){ WriteStatus(); }

void OnTick()
  {
   Risk.RecordSpread();
   bool news=PfmNewsBlackout();
   if(!Risk.OnTickLimits(news)) return;

   datetime bar=iTime(_Symbol,PERIOD_M15,0);
   if(bar==lastBar) return;          // act once per new M15 bar, on the bar that just closed
   lastBar=bar;

   // bar index 1 = just closed. Its close time = bar(0) open time.
   datetime closeTimeServer=bar;
   datetime closeGmt=closeTimeServer-(TimeTradeServer()-TimeGMT());
   int cm=IstMin(closeGmt), day=IstDay(closeGmt);
   if(day==lastSignalDay) return;
   if(cm<=Min(InpTradeStart) || cm>Min(InpTradeEnd)) return;

   // Asian range from today's M15 bars whose IST open in [RangeStart, RangeEnd)
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
   int dir = (c>hi)? 1 : (c<lo)? -1 : 0;
   if(dir==0) return;
   double mid=(hi+lo)/2.0;
   double atrStop=c-dir*InpStopATR*atr[0];
   double stop=(dir>0)? MathMax(mid,atrStop) : MathMin(mid,atrStop);
   double entry=(dir>0)? SymbolInfoDouble(_Symbol,SYMBOL_ASK) : SymbolInfoDouble(_Symbol,SYMBOL_BID);
   if((dir>0 && stop>=entry) || (dir<0 && stop<=entry)) { lastSignalDay=day; return; }
   double target=entry+dir*InpRR*MathAbs(entry-stop);
   stop=NormalizeDouble(stop,_Digits); target=NormalizeDouble(target,_Digits);

   string why;
   double lots=Risk.Check(entry,stop,news,why);
   lastSignalDay=day;                 // one attempt per day, taken or rejected
   if(lots<=0) { Print("PFM rejected: ",why); return; }
   Risk.Open(dir,lots,stop,target,"PFM-A");
  }
