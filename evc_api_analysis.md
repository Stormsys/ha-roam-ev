# EV Charging App API Analysis

## API Base URL
**Production:** `https://europe-west2-prod-evc-app.cloudfunctions.net`

## Authentication
- **Method:** Firebase Authentication
- **Supported:** Email/Password, Google Sign-In, Anonymous
- **Token:** Bearer token (from Firebase Auth getIdToken)
- **Headers:** 
  - `Authorization: Bearer <token>`
  - `X-API-KEY` (for some endpoints)

## API Endpoints

### Authentication (`/evc_auth`)
- `/evc_auth/password_reset` - Password reset
- `/evc_auth/verify_email_address` - Email verification
- `/evc_auth/delete_customer` - Delete user account

### Base Services (`/evc_base`)
- `/evc_base/map/geocoding` - Location services
- `/evc_base/map/places` - Places search
- `/evc_base/map/sites` - Charging sites
- `/evc_base/user/memberships` - User memberships
- `/evc_base/vehicle_enquiry` - Vehicle information

### Charging (`/evc_charge`)
- `/evc_charge/charger/` - Charger details
- `/evc_charge/charger/start` - Start charging
- `/evc_charge/charger/stop` - Stop charging
- `/evc_charge/charger/tariff/rate` - Pricing information
- `/evc_charge/charger/reservation/add` - Add reservation
- `/evc_charge/charger/reservation/delete` - Cancel reservation
- `/evc_charge/charger/transferGuestCharge` - Transfer guest charge
- `/evc_charge/vouchers/` - Voucher management

### Payments (`/evc_payments`)
- `/evc_payments/stripe_customer` - Stripe customer management
- `/evc_payments/stripe_customer/retrieve` - Get customer
- `/evc_payments/stripe_payment_methods` - Payment methods
- `/evc_payments/stripe_payment_methods/primary` - Primary payment
- `/evc_payments/stripe_payment_methods/retrieve` - Get payment method
- `/evc_payments/setup_intent` - Setup payment
- `/evc_payments/payment_intent/pending` - Pending payments
- `/evc_payments/stripe_subscription` - Subscription management
- `/evc_payments/membership_subscription` - Membership subscriptions

### Charge Scheduling (`/evc_chargeSchedule`)
- `/evc_chargeSchedule/addChargeSchedule` - Schedule charging
- `/evc_chargeSchedule/clearChargeSchedulesForUser` - Clear schedules
- `/evc_chargeSchedule/configuration` - Schedule config
- `/evc_chargeSchedule/getNextChargeScheduleForUser` - Next schedule

### Data (`/evc_data`)
- `/evc_data/location` - Location data

## Payment Integration
**Provider:** Stripe
**Live API Key:** `pk_live_51L7g0yI9yAZwaLB31flqEsKUZSZgfWbd8GS9INJMd3wnGVVV10glAuly7mGtDnERuitTCMO22m0erMeFdN9J9KYs00aQKmtkft`
**Merchant ID:** `merchant.net.tecnov8.t8MobileEvcApp`

## Error Tracking
**Sentry DSN:** `https://3aeacdd1f4e74dd2ab0e634ab78c3f3c@o4504729848446976.ingest.sentry.io/4504730236354560`

## App Information
**Package:** `net.tecnov8.t8MobileEvcApp`
**Play Store:** `https://play.google.com/store/apps/details?id=net.tecnov8.t8MobileEvcApp`
**Support:** `https://evcsupport.helpsite.com/`
**Website:** `https://www.evc.co.uk/`

## Feature Flags
- `vouchers`
- `isVoucherEnabled`
- `mobile_app`

## Notes
- Backend hosted on Google Cloud Functions (europe-west2 region - London)
- Uses Firebase for authentication and data storage
- Stripe for payment processing
- Mentions of "staging" environment found in code
