# agyauto

[English](README.md) · [Oʻzbekcha](README.uz.md)

Ruxsat soʻrovlarini qoʻlda tasdiqlashdan charchadingizmi? `agyauto` buyruqni (`agy`, yoki agy ishlatadigan serverga `ssh`) oʻzining
pseudo-terminalida yuritadi va agy'ning "Run this command? / Accept this file edit? / Allow creation of this file?" soʻrovlariga
oʻzi javob beradi. Hamma sessiyalarni kuzatish, toʻxtatish va tarixini koʻrish uchun [btop](https://github.com/aristocratos/btop)
uslubidagi dashboard bor.

```
curl -fsSL https://raw.githubusercontent.com/Sirojiddin-006/agyauto/main/install.sh | sh
```

Linux va macOS, Python 3.8+ (faqat standart kutubxona). Windows: hozircha WSL orqali.

## Ishlatish

```sh
agyauto agy                    # lokal agy
agyauto ssh user@server        # keyin serverda agy'ni ishga tushiring
agyauto --name build ssh ci    # sessiyaga nom berish
agyauto                        # dashboard (istalgan boshqa terminal / workspace'dan)
```

Tugma toʻgʻridan-toʻgʻri oʻralgan buyruqning pty'siga yoziladi. Oyna fokusi, klaviaturangiz yoki boshqa workspace'larga
tegmaydi, shuning uchun boshqa ishlaringizni bemalol qilaverasiz. Istagancha sessiya ishga tushirish mumkin, har biri mustaqil.

### Dashboard

| Tugma | |
|---|---|
| `1`-`5` / Tab | Sessiyalar · Jonli · Tarix · Statistika · Sozlamalar |
| `j` `k` | sessiya / qatorni tanlash |
| `p` | tanlangan sessiyani toʻxtatish / davom ettirish |
| `d` | tanlangan sessiyada **dangermode** yoqish/oʻchirish |
| `r` | sessiyaga nom berish |
| `f` `/` `Enter` | Tarix: tur filtri, qidiruv, batafsil |
| `L` | English ⇄ Oʻzbekcha |
| `q` | chiqish |

Dashboard'dagi oʻzgarishlar ishlab turgan sessiyalarga taxminan bir soniyada yetadi. Qayta ishga tushirish kerak emas, ssh uzilmaydi.

### Xavfsizlik

* Faqat **1-variant** yuboriladi (Enter, yoki `--key 1` bilan `1`). "Always allow (persist to settings.json)" variantlari hech qachon tanlanmaydi.
* **`/` yoki `~` ni oʻchirish (`rm -rf /`, `--no-preserve-root`, ...) hech qachon tasdiqlanmaydi**, dangermode'da ham. Soʻrov ekranda
  qoladi, terminal qoʻngʻiroq beradi, desktop bildirishnoma yuboriladi va hodisa `BLOCKED` deb yoziladi.
* Oʻz taqiq qoidalaringizni (regex) Sozlamalarda yoki `agyauto config set deny 'rm -rf|DROP TABLE'` bilan qoʻshing.
* **Dangermode** qolgan HAMMA narsani, jumladan `press ctrl+j to approve` yoki `(y/n)` kabi nomaʼlum soʻrovlarni ham tasdiqlaydi.
  Standart holatda oʻchiq, har bir sessiyada tasdiqlash soʻralgandan keyin yoqiladi.
* Siz shu terminalda yozayotgan paytda hech narsa yuborilmaydi.
* Token, parol va kalitlar tarixga yozilishidan yoki jonli koʻrinishda chiqishidan oldin yashiriladi. Holat papkasi yopiq (`0700`/`0600`).

Tanilmagan soʻrovlar `STALLED` deb (yashirilgan ekran nusxasi bilan) yoziladi, shunda pattern qoʻshish mumkin. Oʻsha nusxani issue'da yuboring.

## Buyruqlar

```
agyauto status [--json]          ishlayotgan sessiyalar
agyauto history [-n N] [--kind APPROVED|BLOCKED|STALLED] [-s MATN]
agyauto config [get|set KALIT QIYMAT]   lang, key, delay, notify, retention_days, danger_default, deny
agyauto lang en|uz
agyauto doctor
agyauto update
agyauto uninstall [--purge]
```

Fayllar: `~/.config/agyauto/config.json`, `~/.local/state/agyauto/` (history.db, jonli sessiya fayllari), dastur `~/.local/share/agyauto/` da.
Tarix standart boʻyicha 90 kun saqlanadi.

## Ishlab chiqish

```sh
python3 -m unittest discover -s tests -v
```

MIT litsenziya.
