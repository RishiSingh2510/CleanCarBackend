# Backend contract

When `EXPO_PUBLIC_API_URL` is set, the app calls these endpoints (JSON, HTTPS only). Errors must return
a non-2xx status and `{ "message": "Human readable text", "code": "OPTIONAL_CODE" }` — the message is shown to the user.

| Method | Path | Body | Success response |
|---|---|---|---|
| POST | `/auth/login` | `{ identifier, password }` | `{ token, user: { name, identifier } }` |
| POST | `/auth/register` | `{ name, identifier, password }` | `{ token, user: { name, identifier } }` |
| POST | `/auth/forgot-password` | `{ identifier }` | `{}` (always 200 — don't reveal whether the account exists) |
| PATCH | `/account` | `{ name }` | `{ name, identifier }` |
| DELETE | `/account` | — | `{}` — must delete the account and its personal data |

Authenticated calls send `Authorization: Bearer <token>`. A `401` signs the user out automatically.

## Not yet wired to a server (still on-device)

Cars, addresses, bookings, coupons and ratings are stored on the phone (`BookingContext.tsx`). For a real
launch these must move to your server — otherwise bookings never reach your operations team and are lost when the
user changes phone. Suggested resources: `GET/POST /vehicles`, `GET/POST /bookings`,
`POST /bookings/:id/cancel`, `POST /bookings/:id/reschedule`, `POST /bookings/:id/rating`, `POST /coupons/validate`.
Prices, coupon discounts and totals must be **calculated and verified on the server**, not trusted from the app.

## Payments

`src/services/payments.ts` defines a `PaymentProvider`. Register your gateway with `setPaymentProvider()`.
The server must create the order and verify the payment signature; the app must never hold secret keys.
Until a provider is registered, real (non-demo) builds only allow Cash on Delivery.