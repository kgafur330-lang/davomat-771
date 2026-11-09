DAVOMAT.UZ474 — TELEGRAM MINI APP MVP

MUHIM:
Bu ZIP siz yuborgan boshlang'ich kodning ishlaydigan MVP ko'rinishiga keltirilgan versiyasi.
Mini App: Telegram ichida ishlaydi.
Backend: FastAPI + SQLite.
Hozir bor: Telegram initData tekshiruvi, rollar, talabalar ro'yxati, talaba qo'shish,
Super Admin uchun CSV import, dars yaratish, qo'lda davomat belgilash, statistika.
Hozir YO'Q: AI yuzni tanish, kamera qurilmasi bilan integratsiya, offline kamera sync,
talaba uchun to'liq shaxsiy kabinet/attendance foizi. Bu funksiyalarni keyingi bosqichda
kamera va maxfiylik/rozilik talablarini sinab ulash kerak. Hozirgi versiya AI bor deb da'vo qilmaydi.

1) RENDERGA JOYLASH
- Render.com -> New -> Blueprint
- GitHub'ga ZIP ichidagi papkalarni joylang (ZIP'ni GitHub repo ichiga ochib yuklang)
- Render'da render.yaml aniqlanadi va Deploy qiling.
- Environment: BOT_TOKEN qiymatiga BotFather bergan tokenni kiriting.
- SUPER_ADMIN_ID = 474474 (talab qilingan Super Admin ID)
- ADMIN_IDS ga o'qituvchi/admin Telegram raqamli IDlarini vergul bilan kiriting.
- DATABASE_PATH /var/data/davomat.db bo'lib qolishi kerak: persistent disk shu sababli kerak.
Eslatma: Render'da Blueprint yaratishda plan/disk tariflari hisobingizga bog'liq bo'lishi mumkin.

2) TELEGRAM MINI APP ULASH
- BotFather -> /mybots -> botingiz -> Bot Settings -> Menu Button
- Web App URL sifatida Render bergan HTTPS URL'ni kiriting.
- Menu Button nomi: Davomat
- BotFather orqali botga Mini App menyu tugmasini sozlang.
- Mini App'ni bot ichidan ochib tekshiring. Oddiy brauzerda Telegram initData bo'lmagani uchun
  autentifikatsiya rad etiladi.

3) CSV IMPORT
UTF-8 CSV fayl tayyorlang:
student_id,name,group_name
10001,Ali Valiyev,TT-21
10002,Vali Aliyev,TT-22
Super Admin -> Talabalar -> CSV import.

4) LOCAL TEST
Python 3.11+
cd backend
pip install -r requirements.txt
Windows PowerShell:
$env:DEV_MODE="true"
uvicorn app:app --reload
Brauzerda http://127.0.0.1:8000
DEV_MODE faqat lokal test uchun. Internetga chiqarishda false qiling.

5) XAVFSIZLIK
- Bot tokenni hech kimga yubormang va GitHub'ga joylamang.
- Telegram foydalanuvchi ID raqamlari ADMIN_IDS orqali belgilanadi.
- Ishlab chiqarishdan oldin HTTPS, zaxira nusxa, kirish huquqlarini tekshirish,
  shaxsiy ma'lumotlarni himoyalash va talabalar roziligi jarayonini joriy qiling.
- Yuz biometrik ma'lumotlarini roziliksiz yig'mang. Hozir biometrik ma'lumot yig'ilmaydi.
