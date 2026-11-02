//+------------------------------------------------------------------+
//|                                       RangeProfileStructure.mq5   |
//|  MT5 port of "Range Profile Structure [BOSWaves]"                  |
//|  Original: Mozilla Public License 2.0 - (c) BOSWaves               |
//|                                                                    |
//|  Consolidation ranges from alternating swing points, gradient      |
//|  range box, volume profile + POC, breakout / breakdown tags and    |
//|  arrows, position tool (Entry / SL / TP1-3 with price and R),      |
//|  deviation diamonds, range candle colours, telemetry dashboard.    |
//|  Optional true ARGB transparency via a chart canvas.               |
//+------------------------------------------------------------------+
#property copyright "MT5 port of Range Profile Structure [BOSWaves] (MPL-2.0)"
#property version   "1.10"
#property indicator_chart_window
#property indicator_buffers 7
#property indicator_plots   3

#property indicator_label1  "Range Candles"
#property indicator_type1   DRAW_COLOR_CANDLES
#property indicator_label2  "Active Range High"
#property indicator_type2   DRAW_NONE
#property indicator_label3  "Active Range Low"
#property indicator_type3   DRAW_NONE

#include <Canvas/Canvas.mqh>

input group "=============== [1] Swing Engine ==============="
input int    InpSwingLen        = 5;     // Swing Length (Min: 2, Max: 30)
input int    InpSwingMemory     = 10;    // Swing Memory (Min: 4, Max: 20)
input int    InpAtrLen          = 14;    // ATR Length (Min: 2)
enum ENUM_RPS_ATR { ATR_SMA_MT5 = 0, // SMA of True Range (MT5 iATR)
                    ATR_RMA_PINE = 1 // Wilder RMA (TradingView ta.atr)
                  };
input ENUM_RPS_ATR InpAtrMethod = ATR_SMA_MT5; // ATR Method
input int    InpMaxBars         = 2000;  // Max Historical Bars to Process

input group "=============== [2] Range Detection ==============="
input int    InpMinTouches      = 2;     // Touches Per Edge (Min: 2, Max: 5)
input int    InpMinRotations    = 3;     // Minimum Rotations (Min: 3, Max: 10)
input int    InpMinRangeBars    = 8;     // Minimum Range Span (Bars)
input double InpClusterATR      = 0.3;   // Edge Stability ATR (0.05 - 1.0)
input double InpMinWidthATR     = 1.0;   // Minimum Width ATR
input double InpMaxWidthATR     = 6.0;   // Maximum Width ATR
input double InpEdgeAdapt       = 0.2;   // Edge Adaptation (0.0 - 0.50)
input int    InpMaxRangeAge     = 0;     // Maximum Range Age (0 = Disabled)

input group "=============== [3] Volume Profile ==============="
input bool   InpShowProfile     = true;  // Show Range Volume Profile
input int    InpProfileBins     = 14;    // Profile Rows (Min: 8, Max: 16)
input int    InpProfileWidth    = 40;    // Profile Width % (15 - 60)
input bool   InpShowPOC         = true;  // Show Point of Control (POC)
input bool   InpUseRealVolume   = false; // Use Real Volume (false = Tick Volume)

input group "=============== [4] Breakout Structure ==============="
input double InpBreakBuffer     = 0.1;   // Break Buffer ATR (0.0 - 2.0)
input int    InpBreakCloses     = 2;     // Break Acceptance Closes (1 - 5)
input bool   InpShowBreakLabel  = true;  // Show Breakout / Breakdown Tag
input bool   InpShowArrows      = true;  // Show Breakout Arrows (Wingdings 233/234)
input double InpArrowOffsetATR  = 0.15;  // Arrow Wick Offset (ATR Multiplier)
input bool   InpShowDeviations  = true;  // Show Range Deviations (Diamonds)
input int    InpDeviationHistory= 30;    // Deviation History Count

input group "=============== [5] Position & Risk Tool ==============="
input bool   InpShowPosition    = true;  // Show Breakout Position Tool (RR Box)
input int    InpPositionBars    = 10;    // Position Width (Bars Forward)
input double InpTP1             = 0.5;   // TP1 (Range Height Multiple)
input double InpTP2             = 1.0;   // TP2 (Range Height Multiple)
input double InpTP3             = 2.0;   // TP3 (Range Height Multiple)
input bool   InpShowPosLabels   = true;  // Show Position Labels (ENTRY, SL, TP)
input bool   InpLabelPrices     = true;  // Append Exact Price & R:R to Labels

input group "=============== [6] Display & Aesthetics ==============="
input bool   InpUseCanvas       = true;  // Enable True ARGB Transparency Canvas
input int    InpGradientRows    = 22;    // Gradient Smoothness (12 - 24)
input int    InpHistoryCount    = 10;    // Completed Ranges Kept on Chart
input bool   InpPaintCandles    = true;  // Range Candle Colors
input int    InpCandleTransp    = 10;    // Candle Transparency (0 - 70)
input bool   InpShowMidline     = false; // Show Equilibrium (Midline)
input int    InpCooldownBars    = 4;     // New Range Cooldown Bars
input color  InpRangeCol        = C'160,160,160'; // Profile & Mid-Range Color (#A0A0A0)
input color  InpBullCol         = C'0,255,102';   // Bullish Color (#00FF66)
input color  InpBearCol         = C'255,0,102';   // Bearish Color (#FF0066)

input group "=============== [7] Telemetry Dashboard & Alerts ==============="
input bool   InpShowDashboard   = true;  // Show On-Chart Telemetry Dashboard
input int    InpDashX           = 20;    // Dashboard X Offset (Pixels)
input int    InpDashY           = 35;    // Dashboard Y Offset (Pixels)
input bool   InpAlertBreak      = true;  // Alert on Confirmed Breakout/Breakdown
input bool   InpAlertDeviation  = true;  // Alert on Confirmed Range Deviation

//--- buffers
double BufO[], BufH[], BufL[], BufC[], BufClr[], BufTop[], BufBot[];

#define PAL_STEPS 21
#define PAL_BULL  21
#define PAL_BEAR  22

//--- clamped settings
int    SW, MEM, BINS, ROWS, HIST, DEVH;

//--- engine state
string   PFX = "RPS_";
double   g_sp[]; int g_sb[]; int g_ss[]; int g_swCount = 0;
bool     g_active = false;
double   g_top = 0, g_bot = 0;
int      g_left = 0, g_opened = 0, g_hT = 0, g_lT = 0;
int      g_upC = 0, g_dnC = 0, g_cool = 0, g_devDir = 0, g_devBar = 0;
double   g_devExt = 0;
int      g_rangeId = 0, g_profLast = -1, g_lastDone = -1;
double   g_prof[];
double   g_atr[];
double   g_vol[];
int      g_hist[]; int g_histN = 0;
string   g_devNames[]; int g_devN = 0, g_devSeq = 0;
color    g_bg, g_fg;

//--- telemetry
int      g_bullBreaks = 0, g_bearBreaks = 0, g_devHi = 0, g_devLo = 0;
string   g_lastBreak = "---";
color    g_lastBreakCol = clrSilver;

//--- canvas fills
struct FillRec
  {
   string   name;
   datetime t1, t2;
   double   p1, p2;
   uint     argb;
   bool     vis;
  };
FillRec  g_fill[];
int      g_fillN = 0;
CCanvas  g_canvas;
bool     g_canvasOK = false;
string   CANVAS_NAME = "RPSCANVAS_main"; // must not start with PFX (ResetState deletes PFX objects)
datetime g_lastTime = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   SW   = MathMax(2, MathMin(30, InpSwingLen));
   MEM  = MathMax(4, MathMin(20, InpSwingMemory));
   BINS = MathMax(8, MathMin(16, InpProfileBins));
   ROWS = MathMax(12, MathMin(24, InpGradientRows));
   HIST = MathMax(1, InpHistoryCount);
   DEVH = MathMax(1, InpDeviationHistory);

   SetIndexBuffer(0, BufO, INDICATOR_DATA);
   SetIndexBuffer(1, BufH, INDICATOR_DATA);
   SetIndexBuffer(2, BufL, INDICATOR_DATA);
   SetIndexBuffer(3, BufC, INDICATOR_DATA);
   SetIndexBuffer(4, BufClr, INDICATOR_COLOR_INDEX);
   SetIndexBuffer(5, BufTop, INDICATOR_DATA);
   SetIndexBuffer(6, BufBot, INDICATOR_DATA);
   for(int b = 0; b < 3; b++)
      PlotIndexSetDouble(b, PLOT_EMPTY_VALUE, EMPTY_VALUE);

   g_bg = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
   g_fg = (color)ChartGetInteger(0, CHART_COLOR_FOREGROUND);

   PlotIndexSetInteger(0, PLOT_COLOR_INDEXES, PAL_STEPS + 2);
   for(int k = 0; k < PAL_STEPS; k++)
     {
      double pos = k / (double)(PAL_STEPS - 1);
      color c = pos <= 0.5 ? Mix(InpBullCol, InpRangeCol, pos / 0.5) : Mix(InpRangeCol, InpBearCol, (pos - 0.5) / 0.5);
      PlotIndexSetInteger(0, PLOT_LINE_COLOR, k, Fade(c, InpCandleTransp));
     }
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, PAL_BULL, InpBullCol);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, PAL_BEAR, InpBearCol);
   if(!InpPaintCandles)
      PlotIndexSetInteger(0, PLOT_DRAW_TYPE, DRAW_NONE);

   ArrayResize(g_sp, MEM + 1);
   ArrayResize(g_sb, MEM + 1);
   ArrayResize(g_ss, MEM + 1);
   ArrayResize(g_prof, BINS);
   ArrayResize(g_hist, HIST + 2);
   ArrayResize(g_devNames, DEVH + 2);
   ArrayResize(g_fill, 0, 1024);

   if(InpUseCanvas)
     {
      int w = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);
      int h = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
      g_canvasOK = g_canvas.CreateBitmapLabel(0, 0, CANVAS_NAME, 0, 0, MathMax(w, 10), MathMax(h, 10), COLOR_FORMAT_ARGB_NORMALIZE);
      if(g_canvasOK)
        {
         ObjectSetInteger(0, CANVAS_NAME, OBJPROP_BACK, true);
         ObjectSetInteger(0, CANVAS_NAME, OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, CANVAS_NAME, OBJPROP_HIDDEN, true);
        }
      else
         Print("RangeProfileStructure: canvas could not be created, using blended rectangles");
     }
   IndicatorSetString(INDICATOR_SHORTNAME, "Range Profile Structure");
   return(INIT_SUCCEEDED);
  }

void OnDeinit(const int reason)
  {
   ObjectsDeleteAll(0, PFX);
   if(g_canvasOK) g_canvas.Destroy();
   ChartRedraw();
  }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(id == CHARTEVENT_CHART_CHANGE)
     {
      color bg = (color)ChartGetInteger(0, CHART_COLOR_BACKGROUND);
      g_fg = (color)ChartGetInteger(0, CHART_COLOR_FOREGROUND);
      g_bg = bg;
      RedrawCanvas();
     }
  }

//+------------------------------------------------------------------+
//| Colour helpers                                                    |
//+------------------------------------------------------------------+
color Mix(color a, color b, double t) // t=0 -> a, t=1 -> b
  {
   t = MathMax(0.0, MathMin(1.0, t));
   uint ua = (uint)a, ub = (uint)b;
   int r  = (int)MathRound((ua & 0xFF) * (1 - t) + (ub & 0xFF) * t);
   int g  = (int)MathRound(((ua >> 8) & 0xFF) * (1 - t) + ((ub >> 8) & 0xFF) * t);
   int bl = (int)MathRound(((ua >> 16) & 0xFF) * (1 - t) + ((ub >> 16) & 0xFF) * t);
   return((color)(r | (g << 8) | (bl << 16)));
  }
color Fade(color c, double transp) { return(Mix(c, g_bg, transp / 100.0)); } // transp 0..100 (Pine style)

//+------------------------------------------------------------------+
//| Object helpers                                                    |
//+------------------------------------------------------------------+
void ObjRect(string name, datetime t1, double p1, datetime t2, double p2, color c, bool visible)
  {
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_RECTANGLE, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_FILL, true);
      ObjectSetInteger(0, name, OBJPROP_BACK, true);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t1);
   ObjectSetDouble(0, name, OBJPROP_PRICE, 0, p1);
   ObjectSetInteger(0, name, OBJPROP_TIME, 1, t2);
   ObjectSetDouble(0, name, OBJPROP_PRICE, 1, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_TIMEFRAMES, visible ? OBJ_ALL_PERIODS : OBJ_NO_PERIODS);
  }

// a filled area with Pine-style transparency (0 = solid, 100 = invisible)
void Fill(string name, datetime t1, double p1, datetime t2, double p2, color c, double transp, bool visible)
  {
   if(g_canvasOK)
     {
      int idx = -1;
      for(int k = 0; k < g_fillN; k++) if(g_fill[k].name == name) { idx = k; break; }
      if(idx < 0)
        {
         idx = g_fillN++;
         if(ArraySize(g_fill) < g_fillN) ArrayResize(g_fill, g_fillN, 1024);
         g_fill[idx].name = name;
        }
      g_fill[idx].t1 = t1; g_fill[idx].t2 = t2; g_fill[idx].p1 = p1; g_fill[idx].p2 = p2;
      uchar alpha = (uchar)MathMax(0, MathMin(255, (int)MathRound((100.0 - transp) * 2.55)));
      g_fill[idx].argb = ColorToARGB(c, alpha);
      g_fill[idx].vis = visible;
     }
   else
      ObjRect(name, t1, p1, t2, p2, Fade(c, transp), visible);
  }

void DeleteRangeObjects(string prefix)
  {
   ObjectsDeleteAll(0, prefix);
   if(!g_canvasOK) return;
   int w = 0;
   for(int k = 0; k < g_fillN; k++)
      if(StringFind(g_fill[k].name, prefix) != 0) { if(w != k) g_fill[w] = g_fill[k]; w++; }
   g_fillN = w;
  }

void Seg(string name, datetime t1, double p1, datetime t2, double p2, color c, int width, ENUM_LINE_STYLE st, bool visible)
  {
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_TREND, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, name, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, name, OBJPROP_RAY_LEFT, false);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t1);
   ObjectSetDouble(0, name, OBJPROP_PRICE, 0, p1);
   ObjectSetInteger(0, name, OBJPROP_TIME, 1, t2);
   ObjectSetDouble(0, name, OBJPROP_PRICE, 1, p2);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, width);
   ObjectSetInteger(0, name, OBJPROP_STYLE, st);
   ObjectSetInteger(0, name, OBJPROP_TIMEFRAMES, visible ? OBJ_ALL_PERIODS : OBJ_NO_PERIODS);
  }

void Txt(string name, datetime t, double p, string text, color c, int size, ENUM_ANCHOR_POINT anchor)
  {
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_TEXT, 0, t, p);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
      ObjectSetString(0, name, OBJPROP_FONT, "Arial Bold");
     }
   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t);
   ObjectSetDouble(0, name, OBJPROP_PRICE, 0, p);
   ObjectSetString(0, name, OBJPROP_TEXT, text);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_FONTSIZE, size);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
  }

void Arrow(string name, datetime t, double p, int code, color c, ENUM_ARROW_ANCHOR anchor)
  {
   if(ObjectFind(0, name) < 0)
     {
      ObjectCreate(0, name, OBJ_ARROW, 0, t, p);
      ObjectSetInteger(0, name, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, name, OBJPROP_HIDDEN, true);
     }
   ObjectSetInteger(0, name, OBJPROP_TIME, 0, t);
   ObjectSetDouble(0, name, OBJPROP_PRICE, 0, p);
   ObjectSetInteger(0, name, OBJPROP_ARROWCODE, code);
   ObjectSetInteger(0, name, OBJPROP_COLOR, c);
   ObjectSetInteger(0, name, OBJPROP_WIDTH, 2);
   ObjectSetInteger(0, name, OBJPROP_ANCHOR, anchor);
  }

string RName(int id, string part) { return(PFX + IntegerToString(id) + "_" + part); }
string Px(double p) { return(DoubleToString(p, _Digits)); }

//+------------------------------------------------------------------+
//| Canvas drawing                                                    |
//+------------------------------------------------------------------+
int TimeToX(datetime t, datetime lastTime)
  {
   int x = 0, y = 0;
   if(t > lastTime)
     {
      ChartTimePriceToXY(0, 0, lastTime, 0.0, x, y);
      int barPx = 1 << (int)ChartGetInteger(0, CHART_SCALE);
      return(x + (int)((t - lastTime) / PeriodSeconds()) * barPx);
     }
   ChartTimePriceToXY(0, 0, t, 0.0, x, y);
   return(x);
  }

int PriceToY(double p)
  {
   double pmax = ChartGetDouble(0, CHART_PRICE_MAX, 0);
   double pmin = ChartGetDouble(0, CHART_PRICE_MIN, 0);
   int h = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
   if(pmax <= pmin) return(0);
   return((int)MathRound((pmax - p) / (pmax - pmin) * h));
  }

void RedrawCanvas()
  {
   if(!g_canvasOK) return;
   int w = (int)ChartGetInteger(0, CHART_WIDTH_IN_PIXELS);
   int h = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS, 0);
   if(w < 10 || h < 10) return;
   if(g_canvas.Width() != w || g_canvas.Height() != h) g_canvas.Resize(w, h);
   g_canvas.Erase(0);
   datetime lastTime = g_lastTime;
   int barPx = 1 << (int)ChartGetInteger(0, CHART_SCALE);
   for(int k = 0; k < g_fillN; k++)
     {
      if(!g_fill[k].vis) continue;
      int x1 = TimeToX(g_fill[k].t1, lastTime) - barPx / 2;
      int x2 = TimeToX(g_fill[k].t2, lastTime) + barPx / 2;
      int y1 = PriceToY(MathMax(g_fill[k].p1, g_fill[k].p2));
      int y2 = PriceToY(MathMin(g_fill[k].p1, g_fill[k].p2));
      if(x2 < 0 || x1 > w || y2 < 0 || y1 > h) continue;
      x1 = MathMax(0, x1); x2 = MathMin(w - 1, x2);
      y1 = MathMax(0, y1); y2 = MathMin(h - 1, y2);
      if(x2 < x1 || y2 < y1) continue;
      g_canvas.FillRectangle(x1, y1, x2, y2, g_fill[k].argb);
     }
   g_canvas.Update();
  }

//+------------------------------------------------------------------+
//| Swing memory and range search                                     |
//+------------------------------------------------------------------+
void AddSwing(double price, int bi, int side)
  {
   if(g_swCount > 0 && g_ss[0] == side)
     {
      bool rep = (side == 1) ? price >= g_sp[0] : price <= g_sp[0];
      if(rep) { g_sp[0] = price; g_sb[0] = bi; }
      return;
     }
   int lim = MathMin(g_swCount, MEM - 1);
   for(int j = lim; j > 0; j--) { g_sp[j] = g_sp[j - 1]; g_sb[j] = g_sb[j - 1]; g_ss[j] = g_ss[j - 1]; }
   g_sp[0] = price; g_sb[0] = bi; g_ss[0] = side;
   g_swCount = MathMin(g_swCount + 1, MEM);
  }

bool FindRange(int i, double a, double &bTop, double &bBot, int &bLeft, int &bH, int &bL)
  {
   bool found = false;
   int n = g_swCount;
   int minEvents = MathMax(InpMinTouches * 2, InpMinRotations + 1);
   double tol = a * InpClusterATR;
   if(n < minEvents || a <= 0) return(false);
   for(int count = minEvents; count <= n; count++)
     {
      double hs = 0, ls = 0, hmin = 0, hmax = 0, lmin = 0, lmax = 0;
      int hc = 0, lc = 0, oldest = i, newest = 0;
      for(int j = 0; j < count; j++)
        {
         double p = g_sp[j];
         if(g_sb[j] < oldest) oldest = g_sb[j];
         if(g_sb[j] > newest) newest = g_sb[j];
         if(g_ss[j] == 1) { hs += p; hc++; hmin = hc == 1 ? p : MathMin(hmin, p); hmax = hc == 1 ? p : MathMax(hmax, p); }
         else             { ls += p; lc++; lmin = lc == 1 ? p : MathMin(lmin, p); lmax = lc == 1 ? p : MathMax(lmax, p); }
        }
      if(hc >= InpMinTouches && lc >= InpMinTouches)
        {
         double t = hs / hc, b = ls / lc, w = t - b;
         bool stable = (hmax - hmin <= tol * 2.0) && (lmax - lmin <= tol * 2.0);
         bool wOK = (w >= a * InpMinWidthATR) && (w <= a * MathMax(InpMaxWidthATR, InpMinWidthATR));
         bool sOK = (newest - oldest) >= InpMinRangeBars;
         bool rOK = (count - 1) >= InpMinRotations;
         if(t > b && stable && wOK && sOK && rOK)
           { found = true; bTop = t; bBot = b; bLeft = oldest; bH = hc; bL = lc; }
        }
     }
   return(found);
  }

//+------------------------------------------------------------------+
//| Volume profile                                                    |
//+------------------------------------------------------------------+
void AddProfileBar(double lo, double hi, double vol, double bot, double top)
  {
   double h = top - bot;
   if(h <= 0 || vol <= 0) return;
   if(hi == lo)
     {
      if(hi >= bot && hi <= top)
        {
         int idx = (int)MathFloor((hi - bot) / h * BINS);
         idx = MathMax(0, MathMin(BINS - 1, idx));
         g_prof[idx] += vol;
        }
      return;
     }
   double span = MathMax(hi - lo, _Point);
   for(int k = 0; k < BINS; k++)
     {
      double bl = bot + h * k / BINS, bh = bot + h * (k + 1) / BINS;
      double ov = MathMax(0.0, MathMin(hi, bh) - MathMax(lo, bl));
      if(ov > 0) g_prof[k] += vol * ov / span;
     }
  }

void RebuildProfile(int i, int left, double top, double bot, const double &low[], const double &high[])
  {
   ArrayInitialize(g_prof, 0.0);
   int from = MathMax(0, MathMax(left, i - 1500));
   for(int j = from; j <= i; j++)
      AddProfileBar(low[j], high[j], g_vol[j], bot, top);
  }

double PocPrice(double top, double bot, double &maxV)
  {
   maxV = 0; int poc = 0;
   for(int k = 0; k < BINS; k++) if(g_prof[k] > maxV) { maxV = g_prof[k]; poc = k; }
   return(bot + (top - bot) * (poc + 0.5) / BINS);
  }

//+------------------------------------------------------------------+
//| Rendering                                                         |
//+------------------------------------------------------------------+
void RenderRange(int id, int left, int right, double top, double bot, int hT, int lT, color resolved, bool completed, const datetime &time[])
  {
   datetime tL = time[left], tR = time[right];
   double h = MathMax(top - bot, _Point);
   double rh = h / ROWS;
   for(int k = 0; k < ROWS; k++)
     {
      double rTop = top - rh * k, rBot = rTop - rh;
      double pos = (k + 0.5) / ROWS;
      double strength = MathPow(MathAbs(pos - 0.5) * 2.0, 1.55);
      color rc = pos < 0.5 ? InpBearCol : InpBullCol;
      int alpha = (int)(99.0 - strength * (completed ? 17.0 : 38.0));
      Fill(RName(id, "g" + IntegerToString(k)), tL, rTop, tR, rBot, rc, alpha, true);
     }
   int upA = (int)MathMax(4.0, 43.0 - hT * 8.0);
   int loA = (int)MathMax(4.0, 43.0 - lT * 8.0);
   Seg(RName(id, "up"), tL, top, tR, top, Fade(InpBearCol, completed ? 34 : upA), 2, STYLE_SOLID, true);
   Seg(RName(id, "lo"), tL, bot, tR, bot, Fade(InpBullCol, completed ? 34 : loA), 2, STYLE_SOLID, true);
   double mid = (top + bot) / 2.0;
   Seg(RName(id, "mid"), tL, mid, tR, mid, Fade(g_fg, 80), 1, STYLE_DOT, InpShowMidline);

   color css = completed ? resolved : InpRangeCol;
   double maxV;
   double pp = PocPrice(top, bot, maxV);
   int total = MathMax(right - left + 1, 1);
   int maxW = MathMin(MathMax(2, (int)MathRound(total * InpProfileWidth / 100.0)), total);
   for(int k = 0; k < BINS; k++)
     {
      double ratio = maxV > 0 ? g_prof[k] / maxV : 0.0;
      double dens = MathPow(ratio, 0.72);
      double bB = bot + h * k / BINS, bT = bot + h * (k + 1) / BINS;
      bool vis = InpShowProfile && ratio > 0;
      int wb = MathMax(1, (int)MathRound(maxW * MathPow(ratio, 0.85)));
      int li = MathMax(left, right - wb + 1);
      int a = (int)MathMax(42.0, (completed ? 94.0 : 91.0) - dens * (completed ? 30.0 : 42.0));
      Fill(RName(id, "p" + IntegerToString(k)), time[li], bT, tR, bB, css, a, vis);
     }
   Seg(RName(id, "poc"), tL, pp, tR, pp, Fade(g_fg, completed ? 52 : 28), 2, STYLE_SOLID, InpShowPOC && maxV > 0);
  }

void DrawPosition(int id, int dir, int bar, double top, double bot, const datetime &time[])
  {
   if(!InpShowPosition) return;
   double h = top - bot;
   double entry = dir == 1 ? top : bot, stop = dir == 1 ? bot : top;
   double tp1 = entry + dir * h * InpTP1, tp2 = entry + dir * h * InpTP2, tp3 = entry + dir * h * InpTP3;
   datetime t1 = time[bar], t2 = time[bar] + (datetime)(InpPositionBars * PeriodSeconds());
   color css = dir == 1 ? InpBullCol : InpBearCol;
   color oth = dir == 1 ? InpBearCol : InpBullCol;
   Fill(RName(id, "rw"), t1, tp3, t2, entry, css, 88, true);
   Fill(RName(id, "rk"), t1, entry, t2, stop, oth, 93, true);
   Seg(RName(id, "en"), t1, entry, t2, entry, Fade(g_fg, 8), 2, STYLE_SOLID, true);
   Seg(RName(id, "sl"), t1, stop, t2, stop, Fade(g_fg, 52), 1, STYLE_DASH, true);
   Seg(RName(id, "t1"), t1, tp1, t2, tp1, Fade(css, 62), 1, STYLE_DOT, true);
   Seg(RName(id, "t2"), t1, tp2, t2, tp2, Fade(css, 42), 1, STYLE_DOT, true);
   Seg(RName(id, "t3"), t1, tp3, t2, tp3, Fade(css, 20), 1, STYLE_SOLID, true);
   if(InpShowPosLabels)
     {
      string e = " ENTRY", s = " SL", a = " TP1", b = " TP2", c = " TP3";
      if(InpLabelPrices)
        {
         e += " (" + Px(entry) + ")";
         s += " (" + Px(stop) + " | -1.0R)";
         a += " (" + Px(tp1) + " | +" + DoubleToString(InpTP1, 1) + "R)";
         b += " (" + Px(tp2) + " | +" + DoubleToString(InpTP2, 1) + "R)";
         c += " (" + Px(tp3) + " | +" + DoubleToString(InpTP3, 1) + "R)";
        }
      Txt(RName(id, "len"), t2, entry, e, g_fg, 7, ANCHOR_LEFT);
      Txt(RName(id, "lsl"), t2, stop, s, Fade(g_fg, 40), 7, ANCHOR_LEFT);
      Txt(RName(id, "lt1"), t2, tp1, a, Fade(css, 30), 7, ANCHOR_LEFT);
      Txt(RName(id, "lt2"), t2, tp2, b, Fade(css, 20), 7, ANCHOR_LEFT);
      Txt(RName(id, "lt3"), t2, tp3, c, css, 7, ANCHOR_LEFT);
     }
  }

void AddDeviation(datetime t, double price, int dir)
  {
   string nm = PFX + "dev_" + IntegerToString(g_devSeq++);
   Txt(nm, t, price, "◆", dir == 1 ? InpBearCol : InpBullCol, 9, dir == 1 ? ANCHOR_LOWER : ANCHOR_UPPER);
   for(int k = MathMin(g_devN, DEVH); k > 0; k--) g_devNames[k] = g_devNames[k - 1];
   g_devNames[0] = nm;
   g_devN++;
   if(g_devN > DEVH) { ObjectDelete(0, g_devNames[DEVH]); g_devN = DEVH; }
  }

void PushHistory(int id)
  {
   for(int k = MathMin(g_histN, HIST); k > 0; k--) g_hist[k] = g_hist[k - 1];
   g_hist[0] = id;
   g_histN++;
   if(g_histN > HIST) { DeleteRangeObjects(PFX + IntegerToString(g_hist[HIST]) + "_"); g_histN = HIST; }
  }

//+------------------------------------------------------------------+
//| Dashboard                                                         |
//+------------------------------------------------------------------+
void DashLine(int row, string key, string val, color vc)
  {
   string nk = PFX + "dash_k" + IntegerToString(row), nv = PFX + "dash_v" + IntegerToString(row);
   int y = InpDashY + 30 + row * 15;
   if(ObjectFind(0, nk) < 0)
     {
      ObjectCreate(0, nk, OBJ_LABEL, 0, 0, 0);
      ObjectCreate(0, nv, OBJ_LABEL, 0, 0, 0);
      string arr[2]; arr[0] = nk; arr[1] = nv;
      for(int q = 0; q < 2; q++)
        {
         ObjectSetInteger(0, arr[q], OBJPROP_CORNER, CORNER_LEFT_UPPER);
         ObjectSetString(0, arr[q], OBJPROP_FONT, "Consolas");
         ObjectSetInteger(0, arr[q], OBJPROP_FONTSIZE, 8);
         ObjectSetInteger(0, arr[q], OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, arr[q], OBJPROP_HIDDEN, true);
        }
     }
   ObjectSetInteger(0, nk, OBJPROP_XDISTANCE, InpDashX + 10);
   ObjectSetInteger(0, nk, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, nk, OBJPROP_TEXT, StringFormat("%-13s :", key));
   ObjectSetInteger(0, nk, OBJPROP_COLOR, clrSilver);
   ObjectSetInteger(0, nv, OBJPROP_XDISTANCE, InpDashX + 122);
   ObjectSetInteger(0, nv, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, nv, OBJPROP_TEXT, val);
   ObjectSetInteger(0, nv, OBJPROP_COLOR, vc);
  }

void DrawDashboard()
  {
   if(!InpShowDashboard) return;
   string bg = PFX + "dash_bg", tt = PFX + "dash_title";
   if(ObjectFind(0, bg) < 0)
     {
      ObjectCreate(0, bg, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, bg, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, C'20,24,32');
      ObjectSetInteger(0, bg, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, bg, OBJPROP_COLOR, C'60,66,80');
      ObjectSetInteger(0, bg, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, bg, OBJPROP_HIDDEN, true);
      ObjectCreate(0, tt, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, tt, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetString(0, tt, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, tt, OBJPROP_FONTSIZE, 9);
      ObjectSetString(0, tt, OBJPROP_TEXT, "RANGE PROFILE STRUCTURE [BOSWaves]");
      ObjectSetInteger(0, tt, OBJPROP_COLOR, InpBullCol);
      ObjectSetInteger(0, tt, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, tt, OBJPROP_HIDDEN, true);
     }
   ObjectSetInteger(0, bg, OBJPROP_XDISTANCE, InpDashX);
   ObjectSetInteger(0, bg, OBJPROP_YDISTANCE, InpDashY);
   ObjectSetInteger(0, bg, OBJPROP_XSIZE, 315);
   ObjectSetInteger(0, bg, OBJPROP_YSIZE, 30 + 9 * 15 + 8);
   ObjectSetInteger(0, tt, OBJPROP_XDISTANCE, InpDashX + 10);
   ObjectSetInteger(0, tt, OBJPROP_YDISTANCE, InpDashY + 8);

   string status = g_active ? "RANGE ACTIVE" : (g_cool > 0 ? "COOLDOWN (" + IntegerToString(g_cool) + ")" : "SCANNING SWINGS");
   color sc = g_active ? InpBullCol : (g_cool > 0 ? clrOrange : clrSilver);
   DashLine(0, "Engine Status", status, sc);
   if(g_active)
     {
      double maxV; double poc = PocPrice(g_top, g_bot, maxV);
      DashLine(1, "Range Top/Bot", Px(g_top) + " / " + Px(g_bot), clrWhite);
      DashLine(2, "Range POC", maxV > 0 ? Px(poc) : "---", clrGold);
      DashLine(3, "Edge Touches", "High: " + IntegerToString(g_hT) + "  |  Low: " + IntegerToString(g_lT), clrWhite);
      DashLine(4, "Break Closes", "Up: " + IntegerToString(g_upC) + "/" + IntegerToString(InpBreakCloses) +
               "  |  Dn: " + IntegerToString(g_dnC) + "/" + IntegerToString(InpBreakCloses), clrWhite);
     }
   else
     {
      DashLine(1, "Range Top/Bot", "--- / ---", clrGray);
      DashLine(2, "Range POC", "---", clrGray);
      DashLine(3, "Edge Touches", "---", clrGray);
      DashLine(4, "Break Closes", "---", clrGray);
     }
   DashLine(5, "Breaks (B/S)", "Bull: " + IntegerToString(g_bullBreaks) + "  |  Bear: " + IntegerToString(g_bearBreaks), clrWhite);
   DashLine(6, "Deviations", "High: " + IntegerToString(g_devHi) + "  |  Low: " + IntegerToString(g_devLo), clrWhite);
   DashLine(7, "Last Break", g_lastBreak, g_lastBreakCol);
   DashLine(8, "Swings Stored", IntegerToString(g_swCount) + " / " + IntegerToString(MEM) + " Alternating", clrWhite);
  }

//+------------------------------------------------------------------+
void ResetState()
  {
   ObjectsDeleteAll(0, PFX);
   g_fillN = 0;
   g_swCount = 0; g_active = false; g_top = 0; g_bot = 0; g_left = 0; g_opened = 0; g_hT = 0; g_lT = 0;
   g_upC = 0; g_dnC = 0; g_cool = 0; g_devDir = 0; g_devExt = 0; g_devBar = 0;
   g_rangeId = 0; g_profLast = -1; g_lastDone = -1; g_histN = 0; g_devN = 0;
   g_bullBreaks = 0; g_bearBreaks = 0; g_devHi = 0; g_devLo = 0; g_lastBreak = "---"; g_lastBreakCol = clrSilver;
  }

double TrueRange(int i, const double &high[], const double &low[], const double &close[])
  {
   if(i == 0) return(high[0] - low[0]);
   return(MathMax(high[i] - low[i], MathMax(MathAbs(high[i] - close[i - 1]), MathAbs(low[i] - close[i - 1]))));
  }

void CalcATR(int rates_total, int from, const double &high[], const double &low[], const double &close[])
  {
   if(ArraySize(g_atr) < rates_total) ArrayResize(g_atr, rates_total, 2000);
   for(int i = from; i < rates_total; i++)
     {
      if(i < InpAtrLen - 1) { g_atr[i] = 0.0; continue; }
      if(InpAtrMethod == ATR_SMA_MT5 || i == InpAtrLen - 1)
        {
         double s = 0;
         for(int k = i - InpAtrLen + 1; k <= i; k++) s += TrueRange(k, high, low, close);
         g_atr[i] = s / InpAtrLen;
         continue;
        }
      g_atr[i] = (g_atr[i - 1] * (InpAtrLen - 1) + TrueRange(i, high, low, close)) / InpAtrLen;
     }
  }

//+------------------------------------------------------------------+
//| Process one closed bar                                            |
//+------------------------------------------------------------------+
void ProcessBar(int i, bool live, const datetime &time[], const double &high[], const double &low[], const double &close[])
  {
   const int L = SW;
   double a = g_atr[i];
   bool atrOK = i >= InpAtrLen - 1 && a > 0;

   bool hasPh = false, hasPl = false; double ph = 0, pl = 0;
   if(i >= 2 * L)
     {
      double ch = high[i - L], cl = low[i - L];
      bool isH = true, isL = true;
      for(int k = 1; k <= L; k++)
        {
         if(high[i - L - k] >= ch) isH = false;
         if(high[i - L + k] >  ch) isH = false;
         if(low[i - L - k]  <= cl) isL = false;
         if(low[i - L + k]  <  cl) isL = false;
        }
      if(isH) { hasPh = true; ph = ch; }
      if(isL) { hasPl = true; pl = cl; }
     }
   if(hasPh) AddSwing(ph, i - L, 1);
   if(hasPl) AddSwing(pl, i - L, -1);

   if(g_cool > 0) g_cool--;

   if(!g_active && g_cool <= 0 && atrOK)
     {
      double t = 0, b = 0; int lf = 0, hc = 0, lc = 0;
      if(FindRange(i, a, t, b, lf, hc, lc))
        {
         g_active = true; g_top = t; g_bot = b; g_left = MathMax(lf, i - 1500); g_opened = i; g_hT = hc; g_lT = lc;
         g_rangeId++;
         RebuildProfile(i, g_left, g_top, g_bot, low, high);
         g_profLast = i;
         g_upC = 0; g_dnC = 0; g_devDir = 0;
        }
     }

   if(g_active)
     {
      double tol = a * InpClusterATR;
      bool changed = false;
      if(hasPh && i - L >= g_left && MathAbs(ph - g_top) <= tol) { g_top += (ph - g_top) * InpEdgeAdapt; g_hT++; changed = true; }
      if(hasPl && i - L >= g_left && MathAbs(pl - g_bot) <= tol) { g_bot += (pl - g_bot) * InpEdgeAdapt; g_lT++; changed = true; }
      if(changed) { RebuildProfile(i, g_left, g_top, g_bot, low, high); g_profLast = i; }
      else if(i > g_profLast) { AddProfileBar(low[i], high[i], g_vol[i], g_bot, g_top); g_profLast = i; }
     }

   int brk = 0;
   if(g_active)
     {
      double buf = a * InpBreakBuffer;
      bool oUp = close[i] > g_top + buf, oDn = close[i] < g_bot - buf;
      g_upC = oUp ? g_upC + 1 : 0;
      g_dnC = oDn ? g_dnC + 1 : 0;
      if(g_devDir == 0)
        {
         if(oUp)      { g_devDir = 1;  g_devExt = high[i]; g_devBar = i; }
         else if(oDn) { g_devDir = -1; g_devExt = low[i];  g_devBar = i; }
        }
      else
        {
         if(g_devDir == 1 && high[i] > g_devExt) { g_devExt = high[i]; g_devBar = i; }
         if(g_devDir == -1 && low[i] < g_devExt) { g_devExt = low[i]; g_devBar = i; }
         if(close[i] <= g_top && close[i] >= g_bot)
           {
            if(InpShowDeviations) AddDeviation(time[g_devBar], g_devExt, g_devDir);
            if(g_devDir == 1) g_devHi++; else g_devLo++;
            if(live && InpAlertDeviation)
               Alert(_Symbol, " ", EnumToString(_Period), ": Range Profile Structure deviated ", g_devDir == 1 ? "above" : "below",
                     " the range and confirmed back inside");
            g_devDir = 0;
           }
        }
      if(g_upC >= InpBreakCloses) brk = 1;
      if(g_dnC >= InpBreakCloses) brk = -1;
      if(InpMaxRangeAge > 0 && i - g_opened >= InpMaxRangeAge) brk = 2;
     }

   if(g_active && brk != 0)
     {
      color rc = brk == 1 ? InpBullCol : brk == -1 ? InpBearCol : InpRangeCol;
      RenderRange(g_rangeId, g_left, i, g_top, g_bot, g_hT, g_lT, rc, true, time);
      if(brk == 1 || brk == -1)
        {
         double entry = brk == 1 ? g_top : g_bot;
         if(InpShowBreakLabel)
            Txt(RName(g_rangeId, "tag"), time[i], entry, brk == 1 ? " BREAKOUT  ↑" : " BREAKDOWN  ↓", rc, 8, ANCHOR_LEFT);
         if(InpShowArrows)
           {
            if(brk == 1) Arrow(RName(g_rangeId, "arr"), time[i], low[i] - a * InpArrowOffsetATR, 233, rc, ANCHOR_TOP);
            else         Arrow(RName(g_rangeId, "arr"), time[i], high[i] + a * InpArrowOffsetATR, 234, rc, ANCHOR_BOTTOM);
           }
         DrawPosition(g_rangeId, brk, i, g_top, g_bot, time);
         if(brk == 1) { g_bullBreaks++; g_lastBreak = "BULL BREAKOUT @ " + Px(entry); }
         else         { g_bearBreaks++; g_lastBreak = "BEAR BREAKDOWN @ " + Px(entry); }
         g_lastBreakCol = rc;
         if(live && InpAlertBreak)
            Alert(_Symbol, " ", EnumToString(_Period), ": Range Profile Structure broke ", brk == 1 ? "upward" : "downward");
        }
      PushHistory(g_rangeId);
      g_active = false; g_swCount = 0;
      g_upC = 0; g_dnC = 0; g_devDir = 0;
      g_cool = InpCooldownBars;
     }
  }

void PaintBar(int i, const double &open[], const double &high[], const double &low[], const double &close[])
  {
   BufTop[i] = g_active ? g_top : EMPTY_VALUE;
   BufBot[i] = g_active ? g_bot : EMPTY_VALUE;
   if(!(InpPaintCandles && g_active && g_top > g_bot))
     {
      BufO[i] = EMPTY_VALUE; BufH[i] = EMPTY_VALUE; BufL[i] = EMPTY_VALUE; BufC[i] = EMPTY_VALUE; BufClr[i] = 0;
      return;
     }
   BufO[i] = open[i]; BufH[i] = high[i]; BufL[i] = low[i]; BufC[i] = close[i];
   if(close[i] > g_top) { BufClr[i] = PAL_BULL; return; }
   if(close[i] < g_bot) { BufClr[i] = PAL_BEAR; return; }
   double pos = MathMax(0.0, MathMin(1.0, (close[i] - g_bot) / (g_top - g_bot)));
   BufClr[i] = MathRound(pos * (PAL_STEPS - 1));
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
  {
   if(rates_total < 2 * SW + InpAtrLen + 5) return(0);
   ArraySetAsSeries(time, false); ArraySetAsSeries(open, false); ArraySetAsSeries(high, false);
   ArraySetAsSeries(low, false);  ArraySetAsSeries(close, false);
   ArraySetAsSeries(tick_volume, false); ArraySetAsSeries(volume, false);

   if(ArraySize(g_vol) < rates_total) ArrayResize(g_vol, rates_total, 2000);

   bool initial = (prev_calculated == 0 || g_lastDone < 0);
   if(initial)
     {
      ResetState();
      ArrayInitialize(BufO, EMPTY_VALUE); ArrayInitialize(BufH, EMPTY_VALUE);
      ArrayInitialize(BufL, EMPTY_VALUE); ArrayInitialize(BufC, EMPTY_VALUE);
      ArrayInitialize(BufClr, 0);        ArrayInitialize(BufTop, EMPTY_VALUE);
      ArrayInitialize(BufBot, EMPTY_VALUE);
      CalcATR(rates_total, 0, high, low, close);
      for(int k = 0; k < rates_total; k++) g_vol[k] = InpUseRealVolume ? (double)volume[k] : (double)tick_volume[k];
      int start = MathMax(2 * SW, rates_total - 1 - InpMaxBars);
      g_lastDone = start - 1;
     }
   else
     {
      int from = MathMax(1, prev_calculated - 1);
      CalcATR(rates_total, from, high, low, close);
      for(int k = from; k < rates_total; k++) g_vol[k] = InpUseRealVolume ? (double)volume[k] : (double)tick_volume[k];
     }

   int processed = 0;
   for(int i = g_lastDone + 1; i <= rates_total - 2; i++) // closed bars only
     {
      ProcessBar(i, !initial && i == rates_total - 2, time, high, low, close);
      PaintBar(i, open, high, low, close);
      g_lastDone = i;
      processed++;
     }
   if(initial)
      PrintFormat("RangeProfileStructure: processed %d bars, ranges found %d (bull breaks %d, bear breaks %d), active range: %s",
                  processed, g_rangeId, g_bullBreaks, g_bearBreaks, g_active ? "yes" : "no");

   // forming bar: colours and live range extension
   PaintBar(rates_total - 1, open, high, low, close);
   g_lastTime = time[rates_total - 1];
   if(g_active)
      RenderRange(g_rangeId, g_left, rates_total - 1, g_top, g_bot, g_hT, g_lT, InpRangeCol, false, time);
   DrawDashboard();
   RedrawCanvas();
   ChartRedraw();
   return(rates_total);
  }
//+------------------------------------------------------------------+
