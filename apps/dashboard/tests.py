import base64
from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import PrescriberDetails, User
from apps.dashboard.models import Notification
from apps.forms_system.models import BotoxConsentForm

PNG_SIG = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"0" * 16).decode()


class PrescriberAccessTests(TestCase):
    """The prescriber sees clients and their forms, never the calendar, bookings or money."""

    @classmethod
    def setUpTestData(cls):
        cls.practitioner = User.objects.create_superuser(email="owner@example.com", password="x" * 12)
        cls.prescriber   = User.objects.create_user(
            email="dr@example.com", password="x" * 12,
            first_name="Jane", last_name="Smith", role=User.Role.PRESCRIBER,
        )
        PrescriberDetails.objects.create(user=cls.prescriber, title="Dr", registration_number="1234567")
        cls.client_user  = User.objects.create_user(email="client@example.com", password="x" * 12, first_name="Amy")
        cls.botox = BotoxConsentForm.objects.create(
            user=cls.client_user, signature=PNG_SIG,
            full_name="Amy", date_of_birth=date(1990, 1, 1), email="client@example.com",
            client_signed=True,
        )

    def _prescribe(self, **overrides):
        data = {
            "prescriber_face_to_face": "1",
            "prescription_decision":   "prescribed",
            "prescribed_product":      "Botox 100u",
            "prescribed_dose":         "Up to 64 units",
            "prescriber_signature":    PNG_SIG,
            "action":                  "sign",
        }
        data.update(overrides)
        return self.client.post(reverse("forms_system:botox_prescriber", args=[self.botox.pk]), data)

    # ---- What the prescriber can't reach ----

    def test_prescriber_blocked_from_practitioner_pages(self):
        self.client.force_login(self.prescriber)
        blocked = [
            reverse("dashboard:dashboard"),
            reverse("dashboard:bookings_data"),
            reverse("dashboard:closed_dates_page"),
            reverse("dashboard:notifications_page"),
            reverse("dashboard:notifications_data"),
            reverse("dashboard:user_search") + "?q=amy",
            reverse("forms_system:botox_operator", args=[self.botox.pk]),
            reverse("forms_system:consultation_new", args=[self.client_user.pk]),
            reverse("forms_system:record_card_new", args=[self.client_user.pk]),
            reverse("dashboard:note_new", args=[self.client_user.pk]),
        ]
        for url in blocked:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_prescriber_cannot_edit_client_or_money(self):
        self.client.force_login(self.prescriber)
        for name in ("client_edit", "credit_adjust", "bundle_add"):
            with self.subTest(name=name):
                r = self.client.post(reverse(f"dashboard:{name}", args=[self.client_user.pk]), "{}", content_type="application/json")
                self.assertEqual(r.status_code, 302)

    def test_client_profile_hides_bookings_history_bundles_and_credit(self):
        self.client.force_login(self.prescriber)
        data = self.client.get(reverse("dashboard:client_profile", args=[self.client_user.pk])).json()
        self.assertIn("upcoming_bookings", data)
        self.assertIn("forms", data)
        for key in ("past_bookings", "bundles", "credit", "treatments"):
            self.assertNotIn(key, data)

    # ---- What the prescriber can reach ----

    def test_prescriber_can_see_clients_and_forms(self):
        self.client.force_login(self.prescriber)
        self.assertEqual(self.client.get(reverse("dashboard:clients_page")).status_code, 200)
        self.assertEqual(self.client.get(reverse("forms_system:consultation_view", args=[self.client_user.pk])).status_code, 200)
        self.assertEqual(self.client.get(reverse("forms_system:form_status", args=[self.client_user.pk])).status_code, 200)

        emails = [c["email"] for c in self.client.get(reverse("dashboard:client_list")).json()["clients"]]
        self.assertEqual(emails, ["client@example.com"])  # not the prescriber or practitioner

    def test_practitioner_still_has_full_access(self):
        self.client.force_login(self.practitioner)
        self.assertEqual(self.client.get(reverse("dashboard:dashboard")).status_code, 200)
        data = self.client.get(reverse("dashboard:client_profile", args=[self.client_user.pk])).json()
        self.assertIn("credit", data)

    def test_clients_cannot_reach_staff_pages(self):
        self.client.force_login(self.client_user)
        for url in (reverse("dashboard:clients_page"), reverse("forms_system:botox_prescriber", args=[self.botox.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 302)

    def test_profile_sends_prescriber_to_my_account(self):
        self.client.force_login(self.prescriber)
        self.assertRedirects(self.client.get(reverse("accounts:profile")), reverse("dashboard:prescriber_home"))

    # ---- Signing the prescription ----

    def test_prescriber_signs_and_details_are_snapshotted(self):
        self.client.force_login(self.prescriber)
        page = self.client.get(reverse("forms_system:botox_prescriber", args=[self.botox.pk]))
        self.assertContains(page, "Save &amp; Sign")
        self.assertContains(page, "GMC 1234567")

        self.assertEqual(self._prescribe().status_code, 302)

        self.botox.refresh_from_db()
        self.assertTrue(self.botox.prescriber_signed)
        self.assertTrue(self.botox.is_prescribed)
        self.assertEqual(self.botox.prescriber, self.prescriber)
        self.assertEqual(self.botox.prescriber_name, "Dr Jane Smith")
        self.assertEqual(self.botox.prescriber_registration, "GMC 1234567")
        self.assertTrue(Notification.objects.filter(form_type=Notification.FORM_BOTOX_PRESCRIBED, form_id=self.botox.pk).exists())

        # The practitioner sees the signed prescription on the operator page.
        self.client.force_login(self.practitioner)
        operator_page = self.client.get(reverse("forms_system:botox_operator", args=[self.botox.pk]))
        self.assertContains(operator_page, "Dr Jane Smith")
        self.assertNotContains(operator_page, "Awaiting prescription")

    def test_prescription_editable_until_completed_then_locked(self):
        self.client.force_login(self.prescriber)
        self._prescribe()
        self._prescribe(prescribed_product="Botox 50u")
        self.botox.refresh_from_db()
        self.assertEqual(self.botox.prescribed_product, "Botox 50u")

        BotoxConsentForm.objects.filter(pk=self.botox.pk).update(finalised=True)
        self._prescribe(prescribed_product="Something else")
        self.botox.refresh_from_db()
        self.assertEqual(self.botox.prescribed_product, "Botox 50u")

    def test_practitioner_cannot_sign_prescription(self):
        self.client.force_login(self.practitioner)
        self.assertEqual(self.client.get(reverse("forms_system:botox_prescriber", args=[self.botox.pk])).status_code, 200)
        self._prescribe()
        self.botox.refresh_from_db()
        self.assertFalse(self.botox.prescriber_signed)

    def test_prescriber_without_registration_cannot_sign(self):
        self.prescriber.prescriber_details.delete()
        self.prescriber.refresh_from_db()
        self.client.force_login(self.prescriber)
        self._prescribe()
        self.botox.refresh_from_db()
        self.assertFalse(self.botox.prescriber_signed)

    def test_face_to_face_confirmation_and_product_required(self):
        self.client.force_login(self.prescriber)
        self._prescribe(prescriber_face_to_face="")
        self._prescribe(prescribed_product="")
        self.botox.refresh_from_db()
        self.assertFalse(self.botox.prescriber_signed)

    def test_not_suitable_needs_no_product(self):
        self.client.force_login(self.prescriber)
        self._prescribe(prescription_decision="not_suitable", prescribed_product="", prescribed_dose="")
        self.botox.refresh_from_db()
        self.assertTrue(self.botox.prescriber_signed)
        self.assertFalse(self.botox.is_prescribed)


class PrescriberAccountTests(TestCase):
    """The prescriber's My Account page: worklist, details, password, signed history."""

    @classmethod
    def setUpTestData(cls):
        cls.practitioner = User.objects.create_superuser(email="owner@example.com", password="x" * 12)
        cls.prescriber   = User.objects.create_user(
            email="dr@example.com", password="old-password-123",
            first_name="Jane", last_name="Smith", role=User.Role.PRESCRIBER,
        )
        PrescriberDetails.objects.create(user=cls.prescriber, title="Dr", registration_number="1234567")
        cls.other_prescriber = User.objects.create_user(email="dr2@example.com", password="x" * 12, role=User.Role.PRESCRIBER)

    def make_form(self, name, **fields):
        user = User.objects.create_user(email=f"{name.lower()}@example.com", password="x" * 12, first_name=name)
        defaults = dict(user=user, signature=PNG_SIG, full_name=name, date_of_birth=date(1990, 1, 1),
                        email=user.email, client_signed=True)
        defaults.update(fields)
        return BotoxConsentForm.objects.create(**defaults)

    def setUp(self):
        self.client.force_login(self.prescriber)

    def test_only_prescribers_can_open_it(self):
        url = reverse("dashboard:prescriber_home")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.practitioner)
        self.assertEqual(self.client.get(url).status_code, 302)

    def book(self, user, when):
        from apps.bookings.models import Booking
        from apps.treatments.models import Treatment, TreatmentCategory
        cat, _ = TreatmentCategory.objects.get_or_create(name="Injectables")
        tx, _  = Treatment.objects.get_or_create(name="Botox", category=cat, defaults={"duration_minutes": 30, "price": 100})
        Booking.objects.create(user=user, treatment=tx, date=when, start_time="23:00")

    def worklists(self):
        ctx = self.client.get(reverse("dashboard:prescriber_home")).context
        return [f.pk for f in ctx["awaiting"]], [f.pk for f in ctx["unbooked"]]

    def test_worklist_shows_only_forms_awaiting_signature(self):
        waiting  = self.make_form("Waiting")
        self.make_form("Signed", prescriber_signed=True, prescriber=self.prescriber)
        self.make_form("Done", prescriber_signed=True, finalised=True)
        self.make_form("Withdrawn", withdrawn=True)
        self.make_form("Unsigned", client_signed=False)

        awaiting, unbooked = self.worklists()
        self.assertEqual(awaiting + unbooked, [waiting.pk])

    def test_worklist_splits_by_appointment_soonest_first(self):
        later  = self.make_form("Later")
        sooner = self.make_form("Sooner")
        none   = self.make_form("NoBooking")
        today = date.today()
        self.book(later.user, today.replace(year=today.year + 1))
        self.book(sooner.user, today)

        awaiting, unbooked = self.worklists()
        self.assertEqual(awaiting, [sooner.pk, later.pk])
        self.assertEqual(unbooked, [none.pk])

    def test_badge_counts_only_booked_clients(self):
        self.book(self.make_form("Booked").user, date.today())
        self.make_form("NotBooked")
        page = self.client.get(reverse("dashboard:prescriber_home"))
        self.assertContains(page, '<span class="dash-count-badge">1</span>', html=True)
        self.assertContains(page, "No appointment booked (1)")

    def test_worklist_flags_changed_answers(self):
        f = self.make_form("Changed")
        f.log_revision(self.prescriber, "prescriber", "signed")
        f.log_revision(f.user, "prescriber", "signature_withdrawn")
        page = self.client.get(reverse("dashboard:prescriber_home"))
        self.assertEqual(page.context["unbooked"][0].worklist_status, "changed")
        self.assertContains(page, "Client changed answers")

    def test_signing_returns_to_worklist(self):
        f = self.make_form("Amy")
        r = self.client.post(reverse("forms_system:botox_prescriber", args=[f.pk]), {
            "action": "sign", "prescriber_face_to_face": "1", "prescription_decision": "prescribed",
            "prescribed_product": "Botox 100u", "prescribed_dose": "Up to 64 units", "prescriber_signature": PNG_SIG,
        })
        self.assertRedirects(r, reverse("dashboard:prescriber_home"))
        self.assertEqual(self.worklists(), ([], []))
        signed = self.client.get(reverse("dashboard:prescriber_home")).context["signed"]
        self.assertEqual([s.pk for s in signed], [f.pk])

    def test_signed_history_is_only_their_own(self):
        self.make_form("Mine", prescriber_signed=True, prescriber=self.prescriber)
        self.make_form("Theirs", prescriber_signed=True, prescriber=self.other_prescriber)
        signed = self.client.get(reverse("dashboard:prescriber_home")).context["signed"]
        self.assertEqual([s.full_name for s in signed], ["Mine"])

    def test_update_details_but_not_registration(self):
        self.client.post(reverse("dashboard:prescriber_home"), {
            "action": "details", "first_name": "Janet", "last_name": "Smith",
            "email": "janet@example.com", "phone_number": "07700 900000",
            "registration_number": "9999999",  # not on the form — must be ignored
        })
        self.prescriber.refresh_from_db()
        self.assertEqual(self.prescriber.first_name, "Janet")
        self.assertEqual(self.prescriber.email, "janet@example.com")
        self.assertEqual(self.prescriber.profile.phone_number, "07700 900000")
        self.assertEqual(self.prescriber.prescriber_details.registration_number, "1234567")

    def test_profile_card_with_panels_closed(self):
        page = self.client.get(reverse("dashboard:prescriber_home"))
        self.assertContains(page, "Dr Jane Smith")
        self.assertContains(page, "GMC 1234567")
        self.assertContains(page, ">JS</div>")  # initials when there's no photo
        self.assertContains(page, 'id="pcardDetails" hidden')
        self.assertContains(page, 'id="pcardPassword" hidden')

    def test_panel_with_errors_stays_open(self):
        page = self.client.post(reverse("dashboard:prescriber_home"), {
            "action": "password", "old_password": "wrong",
            "new_password1": "a-much-better-passphrase-42", "new_password2": "a-much-better-passphrase-42",
        })
        self.assertContains(page, 'id="pcardPassword" >')
        self.assertContains(page, 'id="pcardDetails" hidden')

    def test_email_must_be_unique(self):
        r = self.client.post(reverse("dashboard:prescriber_home"), {
            "action": "details", "first_name": "Jane", "last_name": "Smith", "email": "owner@example.com",
        })
        self.assertContains(r, "already exists")
        self.prescriber.refresh_from_db()
        self.assertEqual(self.prescriber.email, "dr@example.com")

    def test_change_password_keeps_them_logged_in(self):
        r = self.client.post(reverse("dashboard:prescriber_home"), {
            "action": "password", "old_password": "old-password-123",
            "new_password1": "a-much-better-passphrase-42", "new_password2": "a-much-better-passphrase-42",
        })
        self.assertRedirects(r, reverse("dashboard:prescriber_home"))
        self.prescriber.refresh_from_db()
        self.assertTrue(self.prescriber.check_password("a-much-better-passphrase-42"))
        self.assertEqual(self.client.get(reverse("dashboard:prescriber_home")).status_code, 200)
