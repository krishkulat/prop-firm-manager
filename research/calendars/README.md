# Calendars

## `sge_holidays.csv` (R-005 item 1, for H-003)
Weekdays with no Shanghai Gold Exchange day session. Columns: `date` (Beijing date), `reason`. Weekends are left out because SGE is closed on them
anyway; working Saturdays in China are not trading days on SGE, and its notices list them as closed.

**Coverage: 2021-01-01 to 2026-12-31. 2019 and 2020 are missing.** No SGE notice for those years was found. Do not fill them from China's general public
holiday list: Chinese exchanges extended the 2020 Spring Festival closure for COVID, and the SGE reopening date has not been confirmed from an SGE source. A run of H-003 on 2019-2020
is not holiday-filtered until this gap is closed, and must say so.

Night-session cancellations are not listed. They do not affect H-003, which trades the day session.

The path differs from R-005's `data/sge_holidays.csv` because `data/` is git-ignored. Same case as R-011.

Sources (SGE annual trading schedule notices):
- 2021: https://en.sge.com.cn/eng_news_Announcement/10000124
- 2022: https://en.sge.com.cn/eng_news_Announcement/10000677
- 2023: https://mondovisione.com/media-and-resources/news/shanghai-gold-exchange-announcement-of-trading-schedule-during-public-holidays-2-20221228/
- 2024: https://en.sge.com.cn/eng_news_Announcement/10001816
- 2025: https://en.sge.com.cn/eng_news_Announcement/10002127
- 2026: https://mondovisione.com/media-and-resources/news/shanghai-gold-exchange-announcement-on-trading-schedule-during-public-holidays-20251222/
