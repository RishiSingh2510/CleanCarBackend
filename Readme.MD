# CleanCar API (FastAPI, in-memory database)

Backend for the CleanCar mobile app. Everything is stored **in memory**: it's fast and needs no setup, but
**all data is lost when the server restarts**, and it only works with **a single process** (one uvicorn worker).
Great for development, demos and testing the app end to end — not for real customers (see "Going to production").

## Run it

Requires Python 3.10+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell:  .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env               # optional; or set the variables in your shell
SEED_DEMO=true uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Windows PowerShell: `$env:SEED_DEMO="true"; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

* Interactive docs: http://localhost:8000/docs
* `SEED_DEMO=true` creates a demo account: `demo@cleancar.in` / `demo1234`.

## Connect the mobile app

In the Expo project set `EXPO_PUBLIC_API_URL` (`.env`), then restart with `npx expo start -c`:

| Where the app runs | URL |
|---|---|
| Android emulator | `http://10.0.2.2:8000` |
| iOS simulator | `http://localhost:8000` |
| Real phone (same Wi-Fi) | `http://<your computer's LAN IP>:8000` |

Real phones can't reach `localhost`. Release builds should use **HTTPS** (Android blocks plain HTTP by default).

The app currently calls only the auth/account endpoints (login, register, forgot-password, name update, delete).
The vehicle, booking, coupon and slot endpoints below are ready, but the app still keeps those on the device
until its `BookingContext` is switched over to call them.

## Endpoints

Errors always look like `{ "message": "readable text", "code": "MACHINE_CODE" }`. Authenticated routes need
`Authorization: Bearer <token>`.

| Method | Path | Auth | Notes |
|---|---|---|---|
| GET | `/health` | – | liveness |
| POST | `/auth/register` | – | `{name, identifier, password}` → `201 {token, user, expiresAt}` |
| POST | `/auth/login` | – | `{identifier, password}` → `{token, user, expiresAt}` |
| POST | `/auth/logout` | ✔ | revokes the current token |
| POST | `/auth/forgot-password` | – | always `200 {}`; in development the reset token is printed in the server log |
| POST | `/auth/reset-password` | – | `{token, password}`; signs the user out everywhere |
| GET / PATCH / DELETE | `/account` | ✔ | PATCH `{name}`; DELETE removes the account **and all its data** |
| GET | `/services` | – | the catalogue with server-side prices |
| GET | `/coupons` | – | |
| POST | `/quote` | – | `{serviceId, couponCode?}` → subtotal, discount, taxes, total |
| POST | `/coupons/validate` | – | `{code, serviceId}` → the same quote, or a readable error |
| GET | `/slots?date=YYYY-MM-DD` | – | availability of each time slot |
| GET / POST | `/vehicles` | ✔ | `{brand, model, number, fuel, type}` |
| PATCH / DELETE | `/vehicles/{id}` | ✔ | |
| GET | `/bookings?status=Upcoming\|Completed\|Cancelled` | ✔ | |
| POST | `/bookings` | ✔ | `{serviceId, vehicleId, date, time, address:{label,line1,line2}, paymentMethod: upi\|card\|cod, paymentRef?, couponCode?}` |
| GET | `/bookings/{id}` | ✔ | |
| POST | `/bookings/{id}/cancel` · `/reschedule` · `/rating` | ✔ | reschedule `{date,time}`, rating `{rating: 1-5}` |

JSON is camelCase and booking objects use the same field names as the app's TypeScript `Booking` type, plus
`date` (`YYYY-MM-DD`), `displayStatus` (`Upcoming` / `Completed` / `Cancelled`), `paymentStatus`.
Send `date` as the **local calendar date** (`YYYY-MM-DD`), not a UTC timestamp — times are India time (IST, +05:30).

### Rules the server enforces
* **Prices are calculated on the server** (`/services` + coupons); client-sent totals are ignored.
* A slot holds up to `SLOT_CAPACITY` bookings (default 3); cancelling frees the place. The same car can't hold two bookings in a slot.
* Slots must be in the future and within `BOOKING_WINDOW_DAYS` (30).
* Only **upcoming** bookings can be cancelled or rescheduled; only **completed** ones can be rated.
* People can only ever see or change **their own** vehicles and bookings (others get `404`).
* Passwords are hashed with scrypt; session and reset tokens are stored only as SHA-256 hashes; 5 failed logins lock
  an account for 15 minutes; login errors don't reveal whether an account exists.

## Tests

```bash
python -m unittest discover -s tests -t . -v      # or: pytest
```
* `tests/test_services.py` (54 tests) covers the business logic and needs nothing but Python.
* `tests/test_api.py` covers the HTTP layer and runs once FastAPI + httpx are installed (`requirements-dev.txt`).

## Going to production — what this is NOT yet

1. **Persistence.** Replace `app/store.py` and the three `app/services/*` modules' storage with a real database
   (PostgreSQL + SQLAlchemy/SQLModel). The routers and business rules can stay. Until then, restart = data loss and you
   can't run more than one worker/instance.
2. **Payments.** `paymentRef` is stored but **not verified**. Integrate your gateway (create the order and verify the
   signature on the server) before marking a booking `paid`; also trigger real refunds on cancel (`refund_pending` today).
3. **Password-reset delivery.** No email/SMS is sent; the token is only logged in development. Wire a provider into
   `auth_service.request_password_reset` and add a reset page/deep link.
4. **Operations.** Serve behind HTTPS, set `APP_ENV=production` and a strict `CORS_ORIGINS`, add per-IP rate limiting
   (login lockout is per account only), structured logging/monitoring, and backups.