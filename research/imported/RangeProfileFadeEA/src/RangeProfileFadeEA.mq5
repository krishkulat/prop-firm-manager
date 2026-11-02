//+------------------------------------------------------------------+
//|                                          RangeProfileFadeEA.mq5   |
//|  Range Profile Fade - intraday EA                     v1.10        |
//|  Range engine ported from "Range Profile Structure [BOSWaves]"     |
//|  (Mozilla Public License 2.0 - (c) BOSWaves)                       |
//|                                                                    |
//|  Logic: when price closes outside an active range and then closes  |
//|  back inside (failed breakout / deviation), trade back into the    |
//|  range. Stop beyond the deviation extreme, target 2R (or 1R /      |
//|  opposite edge / midline). Flat before the daily close.            |
//|                                                                    |
//|  v1.20: partial take-profit (at R / at range POC), break-even move  |
//|  v1.10: ATR default = MT5 SMA (matches the MT5 indicator);         |
//|         broker time-zone handling with DST (tester + live);        |
//|         no entries in the daily-close gap / Friday close;          |
//|         minimum stop vs spread filter; optional higher-TF trend    |
//|         filter, blocked UTC hours, max trades per day;             |
//|         OnTester score for the optimiser.                          |
//|  For testing and research. Not financial advice.                   |
//+------------------------------------------------------------------+
#property copyright "Range Profile Fade EA"
#property version   "1.22"

#include <Trade/Trade.mqh>

enum ENUM_RPF_TARGET
  {
   TARGET_R_MULTIPLE = 0, // R multiple
   TARGET_OPPOSITE   = 1, // Opposite range edge
   TARGET_MIDLINE    = 2  // Range midline
  };

enum ENUM_RPF_WINDOW
  {
   WINDOW_ALL_DAY = 0,    // All day
   WINDOW_LDN_NY  = 1     // London + NY (07:00-20:00 UTC)
  };

enum ENUM_RPF_ATR
  {
   ATR_SMA_MT5  = 0,      // SMA of True Range (MT5 iATR - same as the MT5 indicator)
   ATR_RMA_PINE = 1       // Wilder RMA (TradingView / GoCharting)
  };

enum ENUM_RPF_TZ
  {
   TZ_AUTO      = 0,      // Auto (live: from terminal clock, tester: "Tester time zone")
   TZ_UTC       = 1,      // UTC / GMT+0 (Exness)
   TZ_NY_CLOSE  = 2,      // GMT+2 / GMT+3 with US DST (MetaQuotes-Demo, IC Markets, most brokers)
   TZ_EU_DST    = 3,      // GMT+2 / GMT+3 with EU DST
   TZ_FIXED     = 4       // Fixed offset (see "Fixed offset hours")
  };

enum ENUM_RPF_PARTIAL
  {
   PARTIAL_OFF       = 0, // Off
   PARTIAL_AT_R      = 1, // At a fixed R multiple
   PARTIAL_AT_POC    = 2, // At the range POC (skip partial if POC unusable)
   PARTIAL_POC_ELSE_R= 3  // At the range POC, else at the fixed R multiple
  };

enum ENUM_RPF_TREND
  {
   TREND_OFF    = 0,      // Off
   TREND_WITH   = 1       // Only fade in the direction of the higher-TF EMA
  };

input group "Range Engine"
input int          InpSwingLen        = 3;     // Swing Length
input int          InpSwingMemory     = 10;    // Swing Memory
input int          InpAtrLen          = 14;    // ATR Length
input ENUM_RPF_ATR InpAtrMethod       = ATR_SMA_MT5; // ATR Method
input int          InpMinTouches      = 2;     // Touches Per Edge
input int          InpMinRotations    = 3;     // Minimum Rotations
input int          InpMinRangeBars    = 8;     // Minimum Range Span (bars)
input double       InpClusterATR      = 0.30;  // Edge Stability ATR
input double       InpMinWidthATR     = 1.0;   // Minimum Width ATR
input double       InpMaxWidthATR     = 6.0;   // Maximum Width ATR
input double       InpEdgeAdapt       = 0.20;  // Edge Adaptation
input double       InpBreakBuffer     = 0.0;   // Break Buffer ATR
input int          InpBreakCloses     = 3;     // Break Acceptance Closes
input int          InpCooldownBars    = 4;     // New Range Cooldown (bars)

input group "Trade Rules"
input ENUM_RPF_TARGET InpTargetMode   = TARGET_R_MULTIPLE; // Target
input double       InpTargetR         = 2.0;   // Target R (R multiple mode). 2 = PF version, 1 = win-rate version
input double       InpSLBufferATR     = 0.10;  // Stop buffer beyond deviation extreme (ATR)
input ENUM_RPF_WINDOW InpWindow       = WINDOW_ALL_DAY; // Entry window
input bool         InpAllowLong       = true;  // Allow longs
input bool         InpAllowShort      = true;  // Allow shorts
input int          InpMaxTradesPerDay = 0;     // Max trades per trading day (0 = no limit)

input group "Filters"
input double       InpMinRiskSpreads  = 4.0;   // Min stop distance, in multiples of current spread (0 = off)
input double       InpMinRiskATR      = 0.0;   // Min stop distance, in ATR (0 = off)
input double       InpMaxRiskATR      = 0.0;   // Max stop distance, in ATR (0 = off)
input ENUM_RPF_TREND InpTrendFilter   = TREND_OFF; // Higher-TF trend filter
input ENUM_TIMEFRAMES InpTrendTF      = PERIOD_H4; // Trend filter timeframe
input int          InpTrendEMA        = 200;   // Trend filter EMA length
input string       InpBlockedHoursUTC = "9";   // Blocked entry hours UTC, e.g. "7,8,13" (empty = none)
input int          InpMaxSpreadPoints = 0;     // Skip entry if spread above this (points, 0 = off)

input group "Session / Time Zone"
input ENUM_RPF_TZ  InpServerTZ        = TZ_AUTO;     // Broker server time zone
input ENUM_RPF_TZ  InpTesterTZ        = TZ_NY_CLOSE; // Tester time zone (used by Auto in the Strategy Tester)
input int          InpFixedOffset     = 0;     // Fixed offset hours (server minus UTC) for "Fixed"
input int          InpFlatHourUTC     = 21;    // Session end hour UTC (21:00 UTC = 02:30 IST)
input int          InpFlatMinutesEarly= 5;     // Close positions this many minutes before session end
input int          InpNoEntryBeforeFlat = 30;  // No new entries in the last N minutes before session end
input int          InpReopenHourUTC   = 23;    // No new entries from session end until this UTC hour (daily break)
input bool         InpFridayEarlyFlat = true;  // Friday: also stop entries 2h before session end
input int          InpFridayFlatHourUTC = 20;  // Friday: close open positions at this UTC hour (-1 = off)
input bool         InpUseBrokerSessions = true;// Also flat before the broker's own daily trading-session end
input bool         InpHolidayRule     = true;  // Early-close holidays (Dec 24/31, Jul 3/4, Thanksgiving Thu/Fri): no entries, flat early
input int          InpHolidayFlatHourUTC = 16; // Holiday flat hour UTC

input group "Exits: Partial / Break-even"
input ENUM_RPF_PARTIAL InpPartialMode = PARTIAL_POC_ELSE_R; // Partial take-profit
input double       InpPartialR        = 1.25;  // Partial at this R multiple (fixed-R modes)
input double       InpPartialPct      = 60.0;  // % of the position to close at the partial
input double       InpPOCMinR         = 0.3;   // POC must be at least this many R from entry
input bool         InpBEAfterPartial  = true;  // Move stop to break-even after the partial
input double       InpBreakEvenR      = 0.0;   // Move stop to break-even at this R without a partial (0 = off)
input int          InpBEOffsetPoints  = 0;     // Break-even offset in points (+ locks in profit)
input int          InpProfileRows     = 14;    // Volume profile rows used to find the POC

input group "Risk"
input double       InpRiskPercent     = 0.5;   // Risk per trade, % of balance (used when Fixed Lots = 0)
input double       InpFixedLots       = 0.0;   // Fixed lots (>0 overrides risk %)

input group "Misc"
input long         InpMagic           = 26110201; // Magic number
input int          InpWarmupBars      = 3000;  // Bars used to warm up the range engine
input bool         InpDebugPrint      = false; // Print signals and skips to the journal

//--- engine state
double   g_sp[];      // swing prices (0 = newest)
long     g_sb[];      // swing bar index
int      g_ss[];      // swing side (1 high, -1 low)
int      g_swCount = 0;

bool     g_rangeActive = false;
double   g_rTop = 0.0, g_rBot = 0.0;
long     g_rLeft = 0;
int      g_upC = 0, g_dnC = 0, g_cooldown = 0, g_devDir = 0;
double   g_devExt = 0.0;

long     g_barIdx = -1;
double   g_atr = 0.0, g_atrSum = 0.0, g_prevClose = 0.0;
int      g_atrN = 0;
double   g_trRing[]; int g_trPos = 0;
bool     g_havePrev = false;
datetime g_lastBarTime = 0;

//--- signal produced by the last processed bar
int      g_sigDir = 0;
double   g_sigExt = 0.0, g_sigTop = 0.0, g_sigBot = 0.0, g_sigAtr = 0.0;
long     g_sigLeft = 0;

//--- open-trade management state
ulong    g_pTicket = 0;
int      g_pDir = 0;
double   g_pEntry = 0.0, g_pRisk = 0.0, g_pPartialPx = 0.0;
bool     g_pPartialDone = false, g_pBEDone = false;

//--- misc
CTrade   g_trade;
int      g_emaHandle = INVALID_HANDLE;
bool     g_blocked[24];
long     g_tradeDay = -1;
int      g_tradesToday = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(InpSwingLen < 2 || InpSwingMemory < 4 || InpAtrLen < 2)
      return(INIT_PARAMETERS_INCORRECT);
   ArrayResize(g_sp, InpSwingMemory + 1);
   ArrayResize(g_sb, InpSwingMemory + 1);
   ArrayResize(g_ss, InpSwingMemory + 1);
   ArrayResize(g_trRing, InpAtrLen);
   ArrayInitialize(g_trRing, 0.0);
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(50);

   // blocked hours
   for(int h0 = 0; h0 < 24; h0++) g_blocked[h0] = false;
   string parts[];
   int np = StringSplit(InpBlockedHoursUTC, ',', parts);
   for(int k = 0; k < np; k++)
     {
      string s = parts[k];
      StringTrimLeft(s); StringTrimRight(s);
      if(StringLen(s) == 0) continue;
      int h = (int)StringToInteger(s);
      if(h >= 0 && h < 24) g_blocked[h] = true;
     }

   if(InpTrendFilter != TREND_OFF)
     {
      g_emaHandle = iMA(_Symbol, InpTrendTF, InpTrendEMA, 0, MODE_EMA, PRICE_CLOSE);
      if(g_emaHandle == INVALID_HANDLE)
        { Print("RangeProfileFade: cannot create trend EMA"); return(INIT_FAILED); }
     }

   // warm up on closed history
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, _Period, 1, InpWarmupBars, r);
   if(n > 0)
     {
      for(int i = 0; i < n; i++)
         ProcessBar(r, i);
      g_lastBarTime = r[n - 1].time;
     }
   g_sigDir = 0;
   PrintFormat("RangeProfileFade v1.10: warmed up on %d bars, range active=%s, server offset now = %d h",
               n, g_rangeActive ? "yes" : "no", ServerOffsetHours(TimeCurrent()));
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   if(g_emaHandle != INVALID_HANDLE) IndicatorRelease(g_emaHandle);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   ManageSessionExit();
   ManageOpenTrade();

   int need = 2 * InpSwingLen + 60;
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, _Period, 1, need, r);
   if(n <= 2 * InpSwingLen)
      return;
   if(r[n - 1].time <= g_lastBarTime)
      return;

   for(int i = 0; i < n; i++)
     {
      if(r[i].time <= g_lastBarTime)
         continue;
      ProcessBar(r, i);
      g_lastBarTime = r[i].time;
      if(i == n - 1 && g_sigDir != 0)
         TryEntry(r[i]);
     }
  }

//+------------------------------------------------------------------+
//| Range engine: process bar i of chronological array r             |
//+------------------------------------------------------------------+
void ProcessBar(const MqlRates &r[], int i)
  {
   g_barIdx++;
   g_sigDir = 0;
   const int L = InpSwingLen;

   // ATR
   double tr = r[i].high - r[i].low;
   if(g_havePrev)
      tr = MathMax(tr, MathMax(MathAbs(r[i].high - g_prevClose), MathAbs(r[i].low - g_prevClose)));
   g_atrN++;
   g_trRing[g_trPos] = tr;
   g_trPos = (g_trPos + 1) % InpAtrLen;
   if(InpAtrMethod == ATR_SMA_MT5)
     {
      if(g_atrN >= InpAtrLen)
        {
         double s = 0;
         for(int k = 0; k < InpAtrLen; k++) s += g_trRing[k];
         g_atr = s / InpAtrLen;
        }
     }
   else if(g_atrN <= InpAtrLen)
     {
      g_atrSum += tr;
      if(g_atrN == InpAtrLen)
         g_atr = g_atrSum / InpAtrLen;
     }
   else
      g_atr = (g_atr * (InpAtrLen - 1) + tr) / InpAtrLen;
   g_prevClose = r[i].close;
   g_havePrev = true;
   bool atrReady = g_atrN >= InpAtrLen;

   // pivots confirmed L bars after the pivot
   bool hasPh = false, hasPl = false;
   double ph = 0.0, pl = 0.0;
   if(i >= 2 * L)
     {
      double ch = r[i - L].high, cl = r[i - L].low;
      bool isH = true, isL = true;
      for(int k = 1; k <= L; k++)
        {
         if(r[i - L - k].high >= ch) isH = false;
         if(r[i - L + k].high >  ch) isH = false;
         if(r[i - L - k].low  <= cl) isL = false;
         if(r[i - L + k].low  <  cl) isL = false;
        }
      if(isH) { hasPh = true; ph = ch; }
      if(isL) { hasPl = true; pl = cl; }
     }
   if(hasPh) AddSwing(ph, g_barIdx - L, 1);
   if(hasPl) AddSwing(pl, g_barIdx - L, -1);

   if(g_cooldown > 0)
      g_cooldown--;

   if(!g_rangeActive && g_cooldown <= 0 && atrReady)
     {
      double top = 0, bot = 0; long left = 0;
      if(FindRange(g_atr, top, bot, left))
        {
         g_rangeActive = true;
         g_rTop = top;
         g_rBot = bot;
         g_rLeft = (left > g_barIdx - 1500) ? left : g_barIdx - 1500;
         g_upC = 0; g_dnC = 0; g_devDir = 0; g_devExt = 0.0;
        }
     }

   if(g_rangeActive)
     {
      double tol = g_atr * InpClusterATR;
      if(hasPh && g_barIdx - L >= g_rLeft && MathAbs(ph - g_rTop) <= tol)
         g_rTop += (ph - g_rTop) * InpEdgeAdapt;
      if(hasPl && g_barIdx - L >= g_rLeft && MathAbs(pl - g_rBot) <= tol)
         g_rBot += (pl - g_rBot) * InpEdgeAdapt;
     }

   int brk = 0;
   if(g_rangeActive)
     {
      double buf = g_atr * InpBreakBuffer;
      double c = r[i].close;
      bool oUp = c > g_rTop + buf;
      bool oDn = c < g_rBot - buf;
      g_upC = oUp ? g_upC + 1 : 0;
      g_dnC = oDn ? g_dnC + 1 : 0;
      if(g_devDir == 0)
        {
         if(oUp)      { g_devDir = 1;  g_devExt = r[i].high; }
         else if(oDn) { g_devDir = -1; g_devExt = r[i].low;  }
        }
      else
        {
         if(g_devDir == 1 && r[i].high > g_devExt) g_devExt = r[i].high;
         if(g_devDir == -1 && r[i].low < g_devExt) g_devExt = r[i].low;
         if(c <= g_rTop && c >= g_rBot)
           {
            g_sigDir = g_devDir;
            g_sigExt = g_devExt;
            g_sigTop = g_rTop;
            g_sigBot = g_rBot;
            g_sigAtr = g_atr;
            g_sigLeft = g_rLeft;
            g_devDir = 0;
            g_devExt = 0.0;
           }
        }
      if(g_upC >= InpBreakCloses) brk = 1;
      if(g_dnC >= InpBreakCloses) brk = -1;
     }

   if(g_rangeActive && brk != 0)
     {
      g_rangeActive = false;
      g_swCount = 0;
      g_upC = 0; g_dnC = 0; g_devDir = 0; g_devExt = 0.0;
      g_cooldown = InpCooldownBars;
     }
  }

//+------------------------------------------------------------------+
void AddSwing(double price, long bi, int side)
  {
   if(g_swCount > 0 && g_ss[0] == side)
     {
      bool rep = (side == 1) ? price >= g_sp[0] : price <= g_sp[0];
      if(rep) { g_sp[0] = price; g_sb[0] = bi; }
      return;
     }
   int lim = MathMin(g_swCount, InpSwingMemory - 1);
   for(int j = lim; j > 0; j--)
     {
      g_sp[j] = g_sp[j - 1];
      g_sb[j] = g_sb[j - 1];
      g_ss[j] = g_ss[j - 1];
     }
   g_sp[0] = price; g_sb[0] = bi; g_ss[0] = side;
   g_swCount = MathMin(g_swCount + 1, InpSwingMemory);
  }

//+------------------------------------------------------------------+
bool FindRange(double atrValue, double &bestTop, double &bestBot, long &bestLeft)
  {
   bool found = false;
   int n = g_swCount;
   int minEvents = MathMax(InpMinTouches * 2, InpMinRotations + 1);
   double tol = atrValue * InpClusterATR;
   if(n < minEvents || atrValue <= 0)
      return(false);
   for(int count = minEvents; count <= n; count++)
     {
      double hs = 0, ls = 0, hmin = 0, hmax = 0, lmin = 0, lmax = 0;
      int hc = 0, lc = 0;
      long oldest = g_barIdx, newest = 0;
      for(int j = 0; j < count; j++)
        {
         double p = g_sp[j];
         if(g_sb[j] < oldest) oldest = g_sb[j];
         if(g_sb[j] > newest) newest = g_sb[j];
         if(g_ss[j] == 1)
           {
            hs += p; hc++;
            hmin = (hc == 1) ? p : MathMin(hmin, p);
            hmax = (hc == 1) ? p : MathMax(hmax, p);
           }
         else
           {
            ls += p; lc++;
            lmin = (lc == 1) ? p : MathMin(lmin, p);
            lmax = (lc == 1) ? p : MathMax(lmax, p);
           }
        }
      if(hc >= InpMinTouches && lc >= InpMinTouches)
        {
         double top = hs / hc, bot = ls / lc, w = top - bot;
         bool stable  = (hmax - hmin <= tol * 2.0) && (lmax - lmin <= tol * 2.0);
         bool widthOK = (w >= atrValue * InpMinWidthATR) && (w <= atrValue * MathMax(InpMaxWidthATR, InpMinWidthATR));
         bool spanOK  = (newest - oldest) >= InpMinRangeBars;
         bool rotOK   = (count - 1) >= InpMinRotations;
         if(top > bot && stable && widthOK && spanOK && rotOK)
           {
            found = true;
            bestTop = top; bestBot = bot; bestLeft = oldest;
           }
        }
     }
   return(found);
  }

//+------------------------------------------------------------------+
//| Time zone                                                         |
//+------------------------------------------------------------------+
// n-th weekday (0=Sunday) of a month; n = -1 for the last one. Returns the day of month.
int NthSunday(int year, int month, int n)
  {
   MqlDateTime d; d.year = year; d.mon = month; d.day = 1; d.hour = 12; d.min = 0; d.sec = 0;
   datetime first = StructToTime(d);
   MqlDateTime f; TimeToStruct(first, f);
   int firstSunday = 1 + (7 - f.day_of_week) % 7;
   if(n > 0) return(firstSunday + 7 * (n - 1));
   int dim = 31;
   if(month == 4 || month == 6 || month == 9 || month == 11) dim = 30;
   int last = firstSunday;
   while(last + 7 <= dim) last += 7;
   return(last);
  }

int OffsetForZone(ENUM_RPF_TZ z, datetime serverTime)
  {
   if(z == TZ_UTC) return(0);
   if(z == TZ_FIXED) return(InpFixedOffset);
   MqlDateTime t; TimeToStruct(serverTime, t);
   int md = t.mon * 100 + t.day;
   bool dst = false;
   if(z == TZ_NY_CLOSE)
     {
      int start = 300 + NthSunday(t.year, 3, 2);   // 2nd Sunday of March
      int end   = 1100 + NthSunday(t.year, 11, 1); // 1st Sunday of November
      dst = (md >= start && md < end);
     }
   else if(z == TZ_EU_DST)
     {
      int start = 300 + NthSunday(t.year, 3, -1);  // last Sunday of March
      int end   = 1000 + NthSunday(t.year, 10, -1);// last Sunday of October
      dst = (md >= start && md < end);
     }
   return(dst ? 3 : 2);
  }

int ServerOffsetHours(datetime serverTime)
  {
   if(InpServerTZ != TZ_AUTO)
      return(OffsetForZone(InpServerTZ, serverTime));
   if(MQLInfoInteger(MQL_TESTER) || MQLInfoInteger(MQL_OPTIMIZATION))
      return(OffsetForZone(InpTesterTZ == TZ_AUTO ? TZ_NY_CLOSE : InpTesterTZ, serverTime));
   // live: compare server clock with GMT
   long diff = (long)(TimeTradeServer() - TimeGMT());
   return((int)MathRound(diff / 3600.0));
  }

datetime ToUTC(datetime serverTime) { return(serverTime - (datetime)(ServerOffsetHours(serverTime) * 3600)); }

int MinuteOfDayUTC(datetime serverTime)
  {
   MqlDateTime dt;
   TimeToStruct(ToUTC(serverTime), dt);
   return(dt.hour * 60 + dt.min);
  }

int DayOfWeekUTC(datetime serverTime)
  {
   MqlDateTime dt;
   TimeToStruct(ToUTC(serverTime), dt);
   return(dt.day_of_week);
  }

// trading-day id; the day boundary sits at the session end (flat) time
long TradingDay(datetime serverTime)
  {
   return((long)MathFloor(((double)ToUTC(serverTime) - InpFlatHourUTC * 3600.0) / 86400.0));
  }

int FlatMinute() { return(InpFlatHourUTC * 60 - InpFlatMinutesEarly); }

// true from the flat time until the reopen hour (handles wrap past midnight)
bool InMinuteWindow(int m, int from, int to)
  {
   from = (from % 1440 + 1440) % 1440;
   to   = (to % 1440 + 1440) % 1440;
   if(from <= to) return(m >= from && m < to);
   return(m >= from || m < to);
  }

bool AfterFlat(datetime serverTime)
  {
   return(InMinuteWindow(MinuteOfDayUTC(serverTime), FlatMinute(), InpReopenHourUTC * 60));
  }

bool EntryAllowedAt(datetime serverTime, string &why)
  {
   int m = MinuteOfDayUTC(serverTime);
   int endMin = InpFlatHourUTC * 60;
   int cutoff = endMin - InpNoEntryBeforeFlat;
   if(InpFridayEarlyFlat && DayOfWeekUTC(serverTime) == 5) cutoff = MathMin(cutoff, endMin - 120);
   if(InMinuteWindow(m, cutoff, InpReopenHourUTC * 60)) { why = "session close / daily break"; return(false); }
   if(DayOfWeekUTC(serverTime) == 6 || (DayOfWeekUTC(serverTime) == 5 && m >= endMin)) { why = "weekend"; return(false); }
   if(g_blocked[m / 60]) { why = "blocked hour"; return(false); }
   if(FridayFlat(serverTime)) { why = "Friday close"; return(false); }
   if(IsEarlyCloseDay(serverTime)) { why = "early-close holiday"; return(false); }
   int toEnd = MinutesToBrokerSessionEnd(serverTime);
   if(toEnd >= 0 && toEnd <= InpNoEntryBeforeFlat) { why = "broker session ending"; return(false); }
   if(InpWindow == WINDOW_LDN_NY && !(m >= 420 && m < 1200)) { why = "outside London+NY"; return(false); }
   return(true);
  }

//+------------------------------------------------------------------+
bool HasPosition(ulong &ticket, datetime &openTime)
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong t = PositionGetTicket(i);
      if(t == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      ticket = t;
      openTime = (datetime)PositionGetInteger(POSITION_TIME);
      return(true);
     }
   return(false);
  }

// minutes until the broker's trade session for today ends (server schedule); -1 if unknown
int MinutesToBrokerSessionEnd(datetime serverTime)
  {
   if(!InpUseBrokerSessions) return(-1);
   MqlDateTime s; TimeToStruct(serverTime, s);
   datetime from = 0, to = 0, lastTo = 0;
   uint idx = 0;
   while(SymbolInfoSessionTrade(_Symbol, (ENUM_DAY_OF_WEEK)s.day_of_week, idx, from, to))
     {
      lastTo = to;
      idx++;
      if(idx > 10) break;
     }
   if(idx == 0) return(-1);
   int endSec = (int)lastTo;               // seconds from 00:00 (24:00 = 86400)
   int nowSec = s.hour * 3600 + s.min * 60 + s.sec;
   if(endSec <= nowSec) return(-1);
   return((endSec - nowSec) / 60);
  }

bool IsEarlyCloseDay(datetime serverTime)
  {
   if(!InpHolidayRule) return(false);
   MqlDateTime d; TimeToStruct(ToUTC(serverTime), d);
   if(d.mon == 12 && (d.day == 24 || d.day == 31)) return(true);
   if(d.mon == 7 && (d.day == 3 || d.day == 4)) return(true);
   if(d.mon == 11)
     {
      // 4th Thursday of November and the Friday after
      MqlDateTime f; f.year = d.year; f.mon = 11; f.day = 1; f.hour = 12; f.min = 0; f.sec = 0;
      MqlDateTime g; TimeToStruct(StructToTime(f), g);
      int firstThu = 1 + (4 - g.day_of_week + 7) % 7;
      int thanks = firstThu + 21;
      if(d.day == thanks || d.day == thanks + 1) return(true);
     }
   return(false);
  }

bool HolidayFlat(datetime serverTime)
  {
   return(IsEarlyCloseDay(serverTime) && MinuteOfDayUTC(serverTime) >= InpHolidayFlatHourUTC * 60
          && MinuteOfDayUTC(serverTime) < InpFlatHourUTC * 60 + 120);
  }

bool FridayFlat(datetime serverTime)
  {
   if(InpFridayFlatHourUTC < 0) return(false);
   return(DayOfWeekUTC(serverTime) == 5 && MinuteOfDayUTC(serverTime) >= InpFridayFlatHourUTC * 60);
  }

void ManageSessionExit()
  {
   ulong ticket; datetime openTime;
   if(!HasPosition(ticket, openTime))
      return;
   datetime now = TimeCurrent();
   bool newDay = TradingDay(now) != TradingDay(openTime);
   int toEnd = MinutesToBrokerSessionEnd(now);
   bool brokerEnd = (toEnd >= 0 && toEnd <= InpFlatMinutesEarly);
   if(AfterFlat(now) || newDay || FridayFlat(now) || HolidayFlat(now) || brokerEnd)
     {
      if(g_trade.PositionClose(ticket) && InpDebugPrint)
         Print("RangeProfileFade: session flat");
     }
  }

bool ExitedSince(datetime t)
  {
   if(!HistorySelect(t, TimeCurrent() + 60))
      return(false);
   for(int i = HistoryDealsTotal() - 1; i >= 0; i--)
     {
      ulong d = HistoryDealGetTicket(i);
      if(d == 0) continue;
      if(HistoryDealGetString(d, DEAL_SYMBOL) != _Symbol) continue;
      if(HistoryDealGetInteger(d, DEAL_MAGIC) != InpMagic) continue;
      long e = HistoryDealGetInteger(d, DEAL_ENTRY);
      if(e == DEAL_ENTRY_OUT || e == DEAL_ENTRY_INOUT || e == DEAL_ENTRY_OUT_BY)
         return(true);
     }
   return(false);
  }

int TrendDirection()
  {
   if(InpTrendFilter == TREND_OFF || g_emaHandle == INVALID_HANDLE) return(0);
   double ema[1];
   if(CopyBuffer(g_emaHandle, 0, 1, 1, ema) != 1) return(0);
   double c = iClose(_Symbol, InpTrendTF, 1);
   if(c <= 0) return(0);
   return(c > ema[0] ? 1 : -1);
  }

//+------------------------------------------------------------------+
double CalcLots(int dir, double entry, double sl)
  {
   double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double vmax = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double vstep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double lots = InpFixedLots;
   if(lots <= 0)
     {
      double loss1 = 0.0;
      ENUM_ORDER_TYPE ot = dir == 1 ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
      if(!OrderCalcProfit(ot, _Symbol, 1.0, entry, sl, loss1) || loss1 == 0.0)
         return(0.0);
      double riskMoney = AccountInfoDouble(ACCOUNT_BALANCE) * InpRiskPercent / 100.0;
      lots = riskMoney / MathAbs(loss1);
     }
   lots = MathFloor(lots / vstep) * vstep;
   if(lots < vmin) return(0.0);
   return(MathMin(lots, vmax));
  }

void Skip(string why)
  {
   if(InpDebugPrint) Print("RangeProfileFade: signal skipped - ", why);
  }

//+------------------------------------------------------------------+
void TryEntry(const MqlRates &bar)
  {
   int devDir = g_sigDir;
   g_sigDir = 0;
   int dir = -devDir;
   if(dir == 1 && !InpAllowLong) return;
   if(dir == -1 && !InpAllowShort) return;

   ulong ticket; datetime ot;
   if(HasPosition(ticket, ot)) return;

   datetime now = TimeCurrent();
   string why = "";
   if(!EntryAllowedAt(now, why)) { Skip(why); return; }
   if(TradingDay(now) != TradingDay(bar.time)) { Skip("signal bar belongs to previous session"); return; }
   if(ExitedSince(bar.time)) { Skip("a trade closed during the signal bar"); return; }

   long day = TradingDay(now);
   if(day != g_tradeDay) { g_tradeDay = day; g_tradesToday = 0; }
   if(InpMaxTradesPerDay > 0 && g_tradesToday >= InpMaxTradesPerDay) { Skip("max trades per day"); return; }

   int spreadPts = (int)SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(InpMaxSpreadPoints > 0 && spreadPts > InpMaxSpreadPoints) { Skip("spread too wide"); return; }

   int trend = TrendDirection();
   if(InpTrendFilter == TREND_WITH && trend != 0 && trend != dir) { Skip("against higher-TF trend"); return; }

   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double pt  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   double entry = dir == 1 ? ask : bid;
   double sl = g_sigExt + devDir * g_sigAtr * InpSLBufferATR;
   double risk = MathAbs(entry - sl);
   double tp;
   if(InpTargetMode == TARGET_MIDLINE)       tp = (g_sigTop + g_sigBot) / 2.0;
   else if(InpTargetMode == TARGET_OPPOSITE) tp = dir == 1 ? g_sigTop : g_sigBot;
   else                                      tp = entry + dir * risk * InpTargetR;

   if(risk <= 0) return;
   if(dir == 1 && (sl >= bid || tp <= ask)) { Skip("price already beyond stop/target"); return; }
   if(dir == -1 && (sl <= ask || tp >= bid)) { Skip("price already beyond stop/target"); return; }

   double spreadPx = ask - bid;
   if(InpMinRiskSpreads > 0 && risk < InpMinRiskSpreads * spreadPx) { Skip("stop too small vs spread"); return; }
   if(InpMinRiskATR > 0 && risk < InpMinRiskATR * g_sigAtr) { Skip("stop too small vs ATR"); return; }
   if(InpMaxRiskATR > 0 && risk > InpMaxRiskATR * g_sigAtr) { Skip("stop too large vs ATR"); return; }

   long stopsLvl = SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   if(MathAbs(entry - sl) < stopsLvl * pt || MathAbs(tp - entry) < stopsLvl * pt) { Skip("inside stops level"); return; }

   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   sl = NormalizeDouble(sl, digits);
   tp = NormalizeDouble(tp, digits);
   double lots = CalcLots(dir, entry, sl);
   if(lots <= 0) { Print("RangeProfileFade: lot size below minimum, signal skipped"); return; }

   bool ok = dir == 1 ? g_trade.Buy(lots, _Symbol, 0.0, sl, tp, "RPF long")
                      : g_trade.Sell(lots, _Symbol, 0.0, sl, tp, "RPF short");
   if(ok)
     {
      g_tradesToday++;
      ulong tk; datetime otm;
      if(HasPosition(tk, otm))
        {
         g_pTicket = tk;
         g_pDir = dir;
         g_pEntry = PositionGetDouble(POSITION_PRICE_OPEN);
         g_pRisk = MathAbs(g_pEntry - sl);
         g_pPartialDone = false;
         g_pBEDone = false;
         g_pPartialPx = PartialPrice(dir, g_pEntry, g_pRisk, tp);
        }
     }
   if(InpDebugPrint || !ok)
      PrintFormat("RangeProfileFade: %s %s lots=%.2f sl=%.2f tp=%.2f range=[%.2f,%.2f] result=%d",
                  dir == 1 ? "BUY" : "SELL", ok ? "sent" : "FAILED", lots, sl, tp, g_sigBot, g_sigTop,
                  g_trade.ResultRetcode());
  }

//+------------------------------------------------------------------+
//| Volume-profile POC of the signal range (tick volume)             |
//+------------------------------------------------------------------+
double RangePOC(double top, double bot)
  {
   int rows = MathMax(4, InpProfileRows);
   double h = top - bot;
   if(h <= 0) return(0.0);
   int count = (int)MathMin(1500, g_barIdx - g_sigLeft + 1);
   if(count < 2) return(0.0);
   MqlRates r[];
   ArraySetAsSeries(r, false);
   int n = CopyRates(_Symbol, _Period, 1, count, r);
   if(n <= 0) return(0.0);
   double prof[];
   ArrayResize(prof, rows);
   ArrayInitialize(prof, 0.0);
   for(int j = 0; j < n; j++)
     {
      double lo = r[j].low, hi = r[j].high, v = (double)r[j].tick_volume;
      if(v < 1.0) v = 1.0;
      if(hi == lo)
        {
         if(hi >= bot && hi <= top)
           {
            int k = (int)MathFloor((hi - bot) / h * rows);
            prof[MathMax(0, MathMin(rows - 1, k))] += v;
           }
         continue;
        }
      for(int k = 0; k < rows; k++)
        {
         double bl = bot + h * k / rows, bh = bot + h * (k + 1) / rows;
         double ov = MathMax(0.0, MathMin(hi, bh) - MathMax(lo, bl));
         if(ov > 0) prof[k] += v * ov / (hi - lo);
        }
     }
   int best = 0;
   for(int k = 1; k < rows; k++) if(prof[k] > prof[best]) best = k;
   return(bot + h * (best + 0.5) / rows);
  }

double PartialPrice(int dir, double entry, double risk, double tp)
  {
   if(InpPartialMode == PARTIAL_OFF || risk <= 0) return(0.0);
   double fixedR = entry + dir * risk * InpPartialR;
   if(InpPartialMode == PARTIAL_AT_R) return(fixedR);
   double poc = RangePOC(g_sigTop, g_sigBot);
   bool pocOK = poc > 0 && (dir == 1 ? (poc >= entry + risk * InpPOCMinR && poc < tp)
                                      : (poc <= entry - risk * InpPOCMinR && poc > tp));
   if(pocOK) return(poc);
   if(InpPartialMode == PARTIAL_POC_ELSE_R) return(fixedR);
   return(0.0); // POC only and POC unusable: no partial
  }

//+------------------------------------------------------------------+
//| Partial take-profit and break-even management                    |
//+------------------------------------------------------------------+
void ManageOpenTrade()
  {
   ulong ticket; datetime ot;
   if(!HasPosition(ticket, ot)) { g_pTicket = 0; return; }
   if(ticket != g_pTicket)
     {
      // EA restarted with an open position: rebuild state from the position
      g_pTicket = ticket;
      long type = PositionGetInteger(POSITION_TYPE);
      g_pDir = type == POSITION_TYPE_BUY ? 1 : -1;
      g_pEntry = PositionGetDouble(POSITION_PRICE_OPEN);
      double sl0 = PositionGetDouble(POSITION_SL);
      g_pRisk = sl0 > 0 ? MathAbs(g_pEntry - sl0) : 0.0;
      g_pBEDone = sl0 > 0 && (g_pDir == 1 ? sl0 >= g_pEntry : sl0 <= g_pEntry);
      g_pPartialDone = g_pBEDone;
      g_pPartialPx = 0.0;
     }
   if(g_pRisk <= 0) return;
   if(!PositionSelectByTicket(ticket)) return;
   double px = g_pDir == 1 ? SymbolInfoDouble(_Symbol, SYMBOL_BID) : SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double tpNow = PositionGetDouble(POSITION_TP);
   double pt = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   int digits = (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS);
   double bePx = NormalizeDouble(g_pEntry + g_pDir * InpBEOffsetPoints * pt, digits);

   // partial take-profit
   if(!g_pPartialDone && g_pPartialPx > 0 && (g_pDir == 1 ? px >= g_pPartialPx : px <= g_pPartialPx))
     {
      double vol = PositionGetDouble(POSITION_VOLUME);
      double vstep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
      double vmin = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
      double closeVol = MathFloor(vol * InpPartialPct / 100.0 / vstep) * vstep;
      g_pPartialDone = true; // try once
      if(closeVol >= vmin && vol - closeVol >= vmin - 1e-9)
        {
         if(g_trade.PositionClosePartial(ticket, closeVol) && InpDebugPrint)
            PrintFormat("RangeProfileFade: partial %.2f lots at %.2f", closeVol, px);
        }
      else if(InpDebugPrint)
         Print("RangeProfileFade: position too small for a partial close");
      if(InpBEAfterPartial && !g_pBEDone && PositionSelectByTicket(ticket))
        {
         bool beOK = g_pDir == 1 ? bePx < SymbolInfoDouble(_Symbol, SYMBOL_BID) : bePx > SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         if(beOK && g_trade.PositionModify(ticket, bePx, PositionGetDouble(POSITION_TP)))
            g_pBEDone = true;
        }
      return;
     }

   // break-even without a partial
   if(InpBreakEvenR > 0 && !g_pBEDone && (g_pDir == 1 ? px >= g_pEntry + g_pRisk * InpBreakEvenR
                                                       : px <= g_pEntry - g_pRisk * InpBreakEvenR))
     {
      bool beOK = g_pDir == 1 ? bePx < SymbolInfoDouble(_Symbol, SYMBOL_BID) : bePx > SymbolInfoDouble(_Symbol, SYMBOL_ASK);
      if(beOK && g_trade.PositionModify(ticket, bePx, tpNow))
         g_pBEDone = true;
     }
  }

//+------------------------------------------------------------------+
//| Optimiser score: rewards profit factor and recovery, needs trades |
//+------------------------------------------------------------------+
double OnTester()
  {
   double trades = TesterStatistics(STAT_TRADES);
   if(trades < 100) return(0.0);
   double pf = TesterStatistics(STAT_PROFIT_FACTOR);
   double rf = TesterStatistics(STAT_RECOVERY_FACTOR);
   if(pf <= 1.0 || rf <= 0) return(0.0);
   return((pf - 1.0) * rf * MathSqrt(trades / 100.0));
  }
//+------------------------------------------------------------------+
