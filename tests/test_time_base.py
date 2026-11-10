"""R-014: the shared EA time base (mql5/Include/PFM/TimeBase.mqh).

The PFM-TIME block is compiled from the .mqh with a C shim, as in R-013, and checked against the tz database:
15-min rounding, the US and EU DST rules, the tester offset from inputs, and the tester / non-tester paths.
The full EAs are NOT compiled here; they still need a MetaEditor compile before any MT5 run.
"""
import re
import shutil
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
TB = ROOT / "mql5/Include/PFM/TimeBase.mqh"
MQH = ROOT / "mql5/Include/PFM/RiskEngine.mqh"
EAS = {k: ROOT / f"mql5/Experts/{v}.mq5" for k, v in
       {"B": "LondonFade_B", "C": "SgeLong_C", "E": "UsOpenImpulse_E"}.items()}
NONE, US, EU, UNSET = 1, 2, 3, 0

SHIM = r"""
#define _DEFAULT_SOURCE
#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <time.h>
typedef long long datetime_t;
#define datetime datetime_t
#define long long long
enum { PFM_DST_UNSET=0, PFM_DST_NONE=1, PFM_DST_US=2, PFM_DST_EU=3 };
typedef struct { int year, mon, day, hour, min, sec, day_of_week, day_of_year; } MqlDateTime;
static void ZeroMemory_(MqlDateTime *t){ memset(t, 0, sizeof *t); }
#define ZeroMemory(t) ZeroMemory_(&(t))
static datetime StructToTime_(MqlDateTime *t){
  struct tm x; memset(&x, 0, sizeof x);
  x.tm_year=t->year-1900; x.tm_mon=t->mon-1; x.tm_mday=t->day; x.tm_hour=t->hour; x.tm_min=t->min; x.tm_sec=t->sec;
  return (datetime)timegm(&x); }
#define StructToTime(t) StructToTime_(&(t))
static void TimeToStruct_(datetime d, MqlDateTime *t){
  time_t s=(time_t)d; struct tm x; gmtime_r(&s,&x);
  t->year=x.tm_year+1900; t->mon=x.tm_mon+1; t->day=x.tm_mday; t->hour=x.tm_hour; t->min=x.tm_min; t->sec=x.tm_sec;
  t->day_of_week=x.tm_wday; t->day_of_year=x.tm_yday; }
#define TimeToStruct(d,t) TimeToStruct_(d,&(t))
%s
#undef long
int main(void){
  char op[4]; long long a,b,c,d,e,f,g;
  while(scanf("%%3s",op)==1){
    if(op[0]=='R'){ scanf("%%lld",&a); printf("%%lld\n",(long long)PfmRound15(a)); }
    else if(op[0]=='D'){ scanf("%%lld %%lld",&a,&b); printf("%%d\n",(int)PfmDstActive((int)a,b)); }
    else if(op[0]=='C'){ scanf("%%lld %%lld %%lld",&a,&b,&c); printf("%%d\n",(int)PfmTesterConfigOk((int)a,(int)b,(int)c)); }
    else if(op[0]=='T'){ scanf("%%lld %%lld %%lld %%lld",&a,&b,&c,&d); printf("%%lld\n",(long long)PfmTesterOffset((int)a,(int)b,(int)c,d)); }
    else if(op[0]=='O'){ scanf("%%lld %%lld %%lld %%lld %%lld %%lld",&a,&b,&c,&d,&e,&f);
      printf("%%lld\n",(long long)PfmSrvOffsetPure(a!=0,(int)b,(int)c,(int)d,e,f)); }
    else if(op[0]=='G'){ scanf("%%lld %%lld %%lld %%lld %%lld %%lld",&a,&b,&c,&d,&e,&f);
      printf("%%lld\n",(long long)PfmGmtNowPure(a!=0,(int)b,(int)c,(int)d,e,f)); }
    else if(op[0]=='S'){ scanf("%%lld %%lld %%lld %%lld %%lld %%lld %%lld",&a,&b,&c,&d,&e,&f,&g);
      printf("%%lld\n",(long long)PfmSrvToGmtPure(a!=0,(int)b,(int)c,(int)d,e,f,g)); }
  }
  return 0; }
"""

needs_cc = pytest.mark.skipif(shutil.which("cc") is None, reason="needs a C compiler")


@pytest.fixture(scope="module")
def tb(tmp_path_factory):
    block = re.search(r"PFM-TIME-BEGIN[^\n]*\n(.*)//--- PFM-TIME-END", TB.read_text(encoding="utf-8"), re.S).group(1)
    d = tmp_path_factory.mktemp("tb")
    src, exe = d / "tb.c", d / "tb"
    src.write_text(SHIM % block, encoding="utf-8")
    subprocess.run(["cc", "-w", "-x", "c", str(src), "-o", str(exe)], check=True)

    def run(lines):
        out = subprocess.run([str(exe)], input="\n".join(lines) + "\n", capture_output=True, text=True,
                             check=True).stdout.split()
        assert len(out) == len(lines)
        return [int(x) for x in out]
    return run


def ts(t):
    return int(pd.Timestamp(t).timestamp())


def hours_and_edges(rule_zone):
    """Every UTC hour 2019-2030 plus the seconds around each DST change of rule_zone."""
    hours = pd.date_range("2019-01-01", "2031-01-01", freq="1h", tz="UTC")
    tz = ZoneInfo(rule_zone)
    off = np.array([t.to_pydatetime().astimezone(tz).utcoffset().total_seconds() for t in hours])
    changes = hours[1:][np.diff(off) != 0]
    extra = [c + pd.Timedelta(seconds=s) for c in changes for s in (-1, 0, 1, 1799, 3599, 3600)]
    return sorted(set(hours) | set(extra)), changes


# ---------------------------------------------------------------- item 1: 15-min rounding
@needs_cc
def test_round15(tb):
    cases = {7199: 7200, 7201: 7200, -1: 0, 1: 0, 449: 0, 450: 900, -450: -900, -449: 0, 10800 + 449: 10800,
             -18001: -18000, 19800 - 1: 19800, 0: 0}
    assert tb([f"R {k}" for k in cases]) == list(cases.values())
    rng = np.random.default_rng(1)
    raw = rng.integers(-14 * 3600, 14 * 3600, 2000)
    want = [int(np.sign(r) * np.floor(abs(r) / 900 + 0.5) * 900) for r in raw]   # MathRound: halves away from zero
    assert tb([f"R {r}" for r in raw]) == want


# ---------------------------------------------------------------- DST rules against the tz database
@needs_cc
@pytest.mark.parametrize("rule, zone", [(US, "America/New_York"), (EU, "Europe/London")])
def test_dst_rule_matches_tz_database(tb, rule, zone):
    times, changes = hours_and_edges(zone)
    assert len(changes) == 24                                     # 2 a year, 2019-2030
    tz = ZoneInfo(zone)
    want = [int(t.to_pydatetime().astimezone(tz).dst().total_seconds() != 0) for t in times]
    assert tb([f"D {rule} {int(t.timestamp())}" for t in times]) == want


@needs_cc
def test_dst_none_is_never_active(tb):
    assert set(tb([f"D {NONE} {ts(t)}" for t in ("2026-01-15", "2026-07-15", "2026-11-01 06:30")])) == {0}


# ---------------------------------------------------------------- item 2: tester offset from inputs
@needs_cc
@pytest.mark.parametrize("rule, w, s, ref", [
    (US, 120, 180, lambda t: 120 + 60 * int(t.astimezone(ZoneInfo("America/New_York")).dst().total_seconds() != 0)),
    (EU, 120, 180, lambda t: int(t.astimezone(ZoneInfo("Europe/Athens")).utcoffset().total_seconds() // 60)),
    (EU, 0, 60, lambda t: int(t.astimezone(ZoneInfo("Europe/London")).utcoffset().total_seconds() // 60)),
    (NONE, 120, 120, lambda t: 120),
    (NONE, -300, -300, lambda t: -300),
])
def test_tester_offset_recovers_true_gmt(tb, rule, w, s, ref):
    zone = "America/New_York" if rule == US else "Europe/London"
    times, _ = hours_and_edges(zone)
    want = [ref(t.to_pydatetime()) * 60 for t in times]
    srv = [int(t.timestamp()) + o for t, o in zip(times, want)]
    got = tb([f"T {rule} {w} {s} {x}" for x in srv])
    # the tester's TimeGMT() is server time, so pass srv as the terminal GMT: it must be ignored
    gmt = tb([f"G 1 {rule} {w} {s} {x} {x}" for x in srv])
    bad = [(t, g, o) for t, g, o in zip(times, got, want) if g != o]
    for t, g, o in bad:                                           # only the repeated hour after a fall-back
        assert t.dayofweek == 6 and t.month in (10, 11) and g == s * 60 and o == w * 60
        assert 0 < (t - t.floor("1D")).total_seconds() < 7 * 3600            # 01:00-02:00 (EU) or 06:00-07:00 UTC (US)
    assert (len(bad) > 0) == (s != w)
    assert all(g == int(t.timestamp()) for t, g, o, x in zip(times, gmt, want, got) if o == x)


@needs_cc
def test_tester_gmt_now_on_known_dates(tb):
    # GMT+2/+3 New York-rule server: 2026-07-15 12:00 UTC is 15:00 server; 2026-01-15 12:00 UTC is 14:00 server
    for utc, srv in (("2026-07-15 12:00", "2026-07-15 15:00"), ("2026-01-15 12:00", "2026-01-15 14:00"),
                     ("2026-03-09 13:30", "2026-03-09 16:30"),    # first Monday of US summer time
                     ("2026-03-30 13:30", "2026-03-30 16:30"),    # EU changed 03-29, US already on summer
                     ("2026-11-02 13:30", "2026-11-02 15:30")):   # first Monday of US winter time
        assert tb([f"G 1 {US} 120 180 {ts(srv)} {ts(srv)}"]) == [ts(utc)]


@needs_cc
def test_tester_srv_to_gmt_uses_the_offset_in_force_then(tb):
    # C reads Friday's bars on Monday; a US change on the Sunday in between must not shift Friday by an hour
    fri_srv, mon_srv = ts("2026-03-06 23:00"), ts("2026-03-09 04:00")       # Fri 21:00 UTC (+2), Mon 01:00 UTC (+3)
    assert tb([f"S 1 {US} 120 180 {fri_srv} {mon_srv} {mon_srv}"]) == [ts("2026-03-06 21:00")]
    assert tb([f"S 1 {US} 120 180 {mon_srv} {mon_srv} {mon_srv}"]) == [ts("2026-03-09 01:00")]
    # and back in autumn: Fri 2026-10-30 21:00 UTC is 00:00 Sat server (+3), Mon 2026-11-02 01:00 UTC is 03:00 (+2)
    assert tb([f"S 1 {US} 120 180 {ts('2026-10-31 00:00')} {ts('2026-11-02 03:00')} {ts('2026-11-02 03:00')}"]) \
        == [ts("2026-10-30 21:00")]


@needs_cc
def test_tester_config_validation(tb):
    cases = {
        (UNSET, 120, 180): 0, (US, -9999, -9999): 0, (US, 120, -9999): 0, (9, 120, 180): 0,
        (US, 120, 181): 0, (US, 900, 960): 0, (NONE, 120, 180): 0,
        (US, 120, 180): 1, (EU, 0, 60): 1, (NONE, 120, 120): 1, (NONE, 330, 330): 1, (US, -300, -240): 1,
    }
    assert tb([f"C {r} {w} {s}" for r, w, s in cases]) == list(cases.values())


# ---------------------------------------------------------------- outside the tester: unchanged apart from rounding
@needs_cc
def test_non_tester_path_uses_terminal_clocks_rounded(tb):
    gmt = ts("2026-11-10 08:00")
    lines, want = [], []
    for raw in (7200, 7199, 7201, 10800 - 1, 10800 + 1, 0, -1, 19800):
        srv = gmt + raw
        lines += [f"O 0 {UNSET} -9999 -9999 {srv} {gmt}", f"G 0 {UNSET} -9999 -9999 {srv} {gmt}"]
        want += [int(np.sign(raw) * np.floor(abs(raw) / 900 + 0.5) * 900), gmt]
    assert tb(lines) == want
    # B's range-start bar (R-011 2): clocks 1 s apart the wrong way no longer move a bar by a minute
    bar_srv = ts("2026-11-10 02:00")                              # 00:00 UTC = 05:30 IST on a +2 server
    assert tb([f"S 0 {UNSET} -9999 -9999 {bar_srv} {gmt + 7199} {gmt}",
               f"S 0 {UNSET} -9999 -9999 {bar_srv} {gmt + 7201} {gmt}"]) == [ts("2026-11-10 00:00")] * 2


@needs_cc
def test_non_tester_ignores_tester_inputs(tb):
    gmt, srv = ts("2026-07-15 12:00"), ts("2026-07-15 15:00")
    assert tb([f"G 0 {US} 0 0 {srv} {gmt}", f"O 0 {NONE} 600 600 {srv} {gmt}"]) == [gmt, 10800]


# ---------------------------------------------------------------- wiring in the EAs and the risk engine
def test_risk_engine_uses_time_base_and_rejects_unset_tester():
    src = MQH.read_text(encoding="utf-8")
    assert "#include <PFM/TimeBase.mqh>" in src
    assert "return PfmGmtNow()+IST_OFFSET_SEC;" in src and "TimeGMT()" not in src
    check = src[src.index("double   Check("):]
    assert check.index('reason="time_base_unset"') < check.index("return NormalizeDouble(lots,2)")
    assert "MQLInfoInteger(MQL_TESTER)) return false;" in src          # news filter off in the tester, documented
    assert "PFM-LIMITS-BEGIN" in src                                    # limits block untouched in place


def test_time_base_mqh_has_no_limit_values():
    src = TB.read_text(encoding="utf-8")
    for k in ("Risk", "DailyStop", "KillDD", "AccountSize"):
        assert k not in src.split("PFM-TIME-BEGIN")[1]


@pytest.mark.parametrize("ea", sorted(EAS))
def test_bce_use_the_shared_helper_only(ea):
    src = EAS[ea].read_text(encoding="utf-8")
    assert "#include <PFM/RiskEngine.mqh>" in src
    oninit = src[src.index("int OnInit()"):src.index("return INIT_SUCCEEDED;")]
    assert oninit.index("if(!PfmTimeBaseInit()) return INIT_PARAMETERS_INCORRECT;") < oninit.index("Risk.Init();")
    for gone in ("TimeGMT()", "TimeTradeServer()", "SrvOffset()"):
        assert gone not in src.replace("PfmSrvOffset()", ""), gone
    assert "PfmSrvToGmt(" in src and "PfmGmtNow()" in src


def test_tester_note_documents_news_off_and_inputs():
    doc = (ROOT / "mql5/TESTER.md").read_text(encoding="utf-8")
    for s in ("InpTesterGmtWinterMin", "InpTesterGmtSummerMin", "InpTesterDstRule",
              "news filter: off (MT5 tester)", "not news-flat", "MetaEditor compile"):
        assert s in doc
