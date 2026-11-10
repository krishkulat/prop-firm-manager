//+------------------------------------------------------------------+
//| PFM TimeBase.mqh — one server-offset / GMT helper for every PFM EA (R-014)
//|
//| Live / demo (not the tester): unchanged from before R-014 except the 15-min rounding.
//|   PfmSrvOffset() = TimeTradeServer() − TimeGMT(), rounded to 15 min (as E had it).
//|   PfmGmtNow()    = TimeGMT().
//|
//| Strategy Tester: TimeGMT() equals the simulated server time there (MQL5 docs, TimeGMT), so the terminal
//|   cannot say where GMT is. The broker's offset must be given in the three InpTester* inputs below:
//|   winter offset, summer offset (minutes east of GMT) and the DST rule the server follows.
//|   Example, a GMT+2 / GMT+3 server that changes with New York: 120, 180, PFM_DST_US.
//|   Unset or invalid in the tester → PfmTimeBaseInit() is false → the EA's OnInit fails, and
//|   CRiskEngine.Check() rejects every order ("time_base_unset") for any EA that does not call it.
//|   Outside the tester these inputs are ignored.
//|
//| News: PfmNewsBlackout() is always false in the tester (no economic calendar there), so a tester run has
//|   no news blackout and no news flatten. See mql5/TESTER.md. Never read a tester result as news-flat.
//+------------------------------------------------------------------+
#ifndef PFM_TIME_BASE_MQH
#define PFM_TIME_BASE_MQH

enum ENUM_PFM_DST
  {
   PFM_DST_UNSET=0,   // not set (tester run refuses to start)
   PFM_DST_NONE =1,   // server offset never changes
   PFM_DST_US   =2,   // changes with New York: 2nd Sunday of March 07:00 UTC to 1st Sunday of November 06:00 UTC
   PFM_DST_EU   =3    // changes with Europe: last Sunday of March 01:00 UTC to last Sunday of October 01:00 UTC
  };

input group "=== PFM time base (Strategy Tester only) ==="
input int          InpTesterGmtWinterMin = -9999;          // server offset from GMT in winter, minutes (e.g. 120)
input int          InpTesterGmtSummerMin = -9999;          // server offset from GMT in summer, minutes (e.g. 180)
input ENUM_PFM_DST InpTesterDstRule      = PFM_DST_UNSET;  // DST rule of the server

//--- PFM-TIME-BEGIN pure arithmetic, no MT5 calls; tests/test_time_base.py compiles this block with a C shim
//--- offset rounded to the nearest 15 min, halves away from zero (as MathRound): a one-second clock difference
//--- must not move a bar off its session minute
long PfmRound15(long rawSec)
  {
   if(rawSec>=0) return ((rawSec+450)/900)*900;
   return -(((-rawSec)+450)/900)*900;
  }
//--- UTC instant of 00:00 on the first Sunday on or after <year>-<month>-<dayFrom>
datetime PfmSundayOnOrAfter(int year,int month,int dayFrom)
  {
   MqlDateTime t;
   ZeroMemory(t);
   t.year=year; t.mon=month; t.day=dayFrom;
   datetime d=StructToTime(t);
   TimeToStruct(d,t);
   return d+(datetime)(((7-t.day_of_week)%7)*86400);
  }
//--- is daylight time in force at a GMT instant under <rule>
bool PfmDstActive(int rule,datetime gmt)
  {
   MqlDateTime t;
   TimeToStruct(gmt,t);
   datetime start=0,end=0;
   if(rule==PFM_DST_US)
     {
      start=PfmSundayOnOrAfter(t.year,3,8)+7*3600;      // 02:00 EST
      end  =PfmSundayOnOrAfter(t.year,11,1)+6*3600;     // 02:00 EDT
     }
   else if(rule==PFM_DST_EU)
     {
      start=PfmSundayOnOrAfter(t.year,3,25)+1*3600;     // last Sunday of March, 01:00 UTC
      end  =PfmSundayOnOrAfter(t.year,10,25)+1*3600;    // last Sunday of October, 01:00 UTC
     }
   else return false;
   return (gmt>=start && gmt<end);
  }
//--- tester inputs usable: rule set, offsets whole quarter hours within ±14 h, NONE means one offset
bool PfmTesterConfigOk(int rule,int winterMin,int summerMin)
  {
   if(rule!=PFM_DST_NONE && rule!=PFM_DST_US && rule!=PFM_DST_EU) return false;
   if(winterMin<-840 || winterMin>840 || summerMin<-840 || summerMin>840) return false;
   if(winterMin%15!=0 || summerMin%15!=0) return false;
   if(rule==PFM_DST_NONE && summerMin!=winterMin) return false;
   return true;
  }
//--- server offset in seconds at a SERVER time, from the tester inputs. The one ambiguous server hour after a
//--- fall-back change (a Sunday, gold closed) is read as summer time.
long PfmTesterOffset(int rule,int winterMin,int summerMin,datetime srv)
  {
   long s=(long)summerMin*60, w=(long)winterMin*60;
   if(rule!=PFM_DST_NONE && PfmDstActive(rule,srv-(datetime)s)) return s;
   return w;
  }
//--- server offset in seconds at server time <srv>. tester: from the inputs. Else: the terminal's clocks, rounded.
long PfmSrvOffsetPure(bool tester,int rule,int winterMin,int summerMin,datetime srv,datetime gmtTerminal)
  {
   if(tester) return PfmTesterOffset(rule,winterMin,summerMin,srv);
   return PfmRound15((long)(srv-gmtTerminal));
  }
//--- GMT now. tester: server time less the input offset. Else: the terminal's GMT, unchanged.
datetime PfmGmtNowPure(bool tester,int rule,int winterMin,int summerMin,datetime srv,datetime gmtTerminal)
  {
   if(tester) return srv-(datetime)PfmTesterOffset(rule,winterMin,summerMin,srv);
   return gmtTerminal;
  }
//--- a past server time (bar open, position open) to GMT. tester: the offset in force at that time.
//--- Else: today's rounded offset, as before R-014 (a DST change between then and now is not seen live).
datetime PfmSrvToGmtPure(bool tester,int rule,int winterMin,int summerMin,datetime srvThen,datetime srvNow,datetime gmtTerminal)
  {
   if(tester) return srvThen-(datetime)PfmTesterOffset(rule,winterMin,summerMin,srvThen);
   return srvThen-(datetime)PfmRound15((long)(srvNow-gmtTerminal));
  }
//--- PFM-TIME-END

bool     PfmIsTester()  { return MQLInfoInteger(MQL_TESTER)!=0; }
bool     PfmTimeBaseOk(){ return !PfmIsTester() || PfmTesterConfigOk((int)InpTesterDstRule,InpTesterGmtWinterMin,InpTesterGmtSummerMin); }
long     PfmSrvOffset() { return PfmSrvOffsetPure(PfmIsTester(),(int)InpTesterDstRule,InpTesterGmtWinterMin,InpTesterGmtSummerMin,TimeTradeServer(),TimeGMT()); }
datetime PfmGmtNow()    { return PfmGmtNowPure(PfmIsTester(),(int)InpTesterDstRule,InpTesterGmtWinterMin,InpTesterGmtSummerMin,TimeTradeServer(),TimeGMT()); }
datetime PfmSrvToGmt(datetime srvThen)
  { return PfmSrvToGmtPure(PfmIsTester(),(int)InpTesterDstRule,InpTesterGmtWinterMin,InpTesterGmtSummerMin,srvThen,TimeTradeServer(),TimeGMT()); }

//--- call first in OnInit; false → return INIT_PARAMETERS_INCORRECT. No silent tester run on wrong hours.
bool PfmTimeBaseInit()
  {
   if(!PfmIsTester()) return true;
   if(!PfmTimeBaseOk())
     {
      Print("PFM time base: set InpTesterGmtWinterMin, InpTesterGmtSummerMin and InpTesterDstRule for this broker "
            "(see mql5/TESTER.md). Tester run refused.");
      return false;
     }
   PrintFormat("PFM time base (tester): winter %+d min, summer %+d min, rule %d. News filter OFF in the tester.",
               InpTesterGmtWinterMin,InpTesterGmtSummerMin,(int)InpTesterDstRule);
   return true;
  }

#endif
