import base64

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import PrescriberDetails, User
from apps.forms_system.models import BotoxConsentForm, BotoxFormRevision

Action = BotoxFormRevision.Action


def png_sig(marker):
    """A valid signature data URL; `marker` makes each one distinguishable."""
    return "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + marker.encode()).decode()


class BotoxLifecycleTests(TestCase):
    """
    Client → prescriber → practitioner, each editing only their own section,
    until the practitioner completes the form and it becomes read-only.
    """

    @classmethod
    def setUpTestData(cls):
        cls.practitioner = User.objects.create_superuser(email="owner@example.com", password="x" * 12, first_name="Owner")
        cls.prescriber   = User.objects.create_user(
            email="dr@example.com", password="x" * 12,
            first_name="Jane", last_name="Smith", role=User.Role.PRESCRIBER,
        )
        PrescriberDetails.objects.create(user=cls.prescriber, title="Dr", registration_number="1234567")
        cls.client_user  = User.objects.create_user(email="client@example.com", password="x" * 12, first_name="Amy")

    # ---- helpers ----

    def client_submits(self, **overrides):
        self.client.force_login(self.client_user)
        data = {
            "full_name": "Amy", "date_of_birth": "1990-01-01", "email": "client@example.com",
            "current_medications": "None", "is_pregnant": "0",
            "consent_agreement": "on", "signature": png_sig("client"),
        }
        data.update(overrides)
        return self.client.post(reverse("forms_system:botox_client"), data)

    def prescriber_saves(self, action="sign", **overrides):
        self.client.force_login(self.prescriber)
        data = {
            "action": action, "prescriber_face_to_face": "1", "prescription_decision": "prescribed",
            "prescribed_product": "Botox 100u", "prescribed_dose": "Up to 64 units",
            "prescriber_signature": png_sig("prescriber"),
        }
        data.update(overrides)
        return self.client.post(reverse("forms_system:botox_prescriber", args=[self.form().pk]), data)

    def practitioner_saves(self, action="sign", **overrides):
        self.client.force_login(self.practitioner)
        data = {"action": action, "units_forehead": "10", "units_total": "10", "operator_signature": png_sig("operator")}
        data.update(overrides)
        return self.client.post(reverse("forms_system:botox_operator", args=[self.form().pk]), data)

    def complete(self, confirm=True):
        self.client.force_login(self.practitioner)
        data = {"action": "complete"}
        if confirm:
            data["confirm_complete"] = "1"
        return self.client.post(reverse("forms_system:botox_operator", args=[self.form().pk]), data)

    def form(self):
        """The client's most recent Botox form."""
        return BotoxConsentForm.objects.filter(user=self.client_user).latest("completed_at")

    # ---- tests ----

    def test_full_lifecycle(self):
        self.client_submits()
        self.client_submits(current_medications="Aspirin")  # client edits — same form
        self.assertEqual(BotoxConsentForm.objects.filter(user=self.client_user).count(), 1)
        self.assertEqual(self.form().current_medications, "Aspirin")

        self.prescriber_saves()
        self.practitioner_saves(action="save")  # progress only
        f = self.form()
        self.assertTrue(f.prescriber_signed)
        self.assertFalse(f.operator_signed)
        self.assertEqual(f.units_forehead, "10")
        self.assertFalse(f.can_finalise)

        self.practitioner_saves()
        self.complete(confirm=False)
        self.assertFalse(self.form().finalised)

        r = self.complete()
        f = BotoxConsentForm.objects.get(user=self.client_user)
        self.assertRedirects(r, reverse("forms_system:botox_view", args=[f.pk]))
        self.assertTrue(f.finalised)
        self.assertEqual(f.finalised_by, self.practitioner)

        # The completed record is viewable by clinical staff, with its history.
        self.client.force_login(self.prescriber)
        page = self.client.get(reverse("forms_system:botox_view", args=[f.pk]))
        self.assertContains(page, "read-only record")
        self.assertContains(page, "Completed — now read-only")

        actions = list(f.revisions.values_list("action", flat=True))
        self.assertEqual(actions, [Action.SUBMITTED, Action.UPDATED, Action.SIGNED, Action.SAVED, Action.SIGNED, Action.COMPLETED])
        # The client's original answer survives in the history.
        self.assertEqual(f.revisions.first().data["current_medications"], "None")

    def test_completed_form_cannot_be_changed_by_anyone(self):
        self.client_submits()
        self.prescriber_saves()
        self.practitioner_saves()
        self.complete()
        done = BotoxConsentForm.objects.get(user=self.client_user)
        revisions = done.revisions.count()

        self.client.force_login(self.prescriber)
        self.client.post(reverse("forms_system:botox_prescriber", args=[done.pk]),
                         {"action": "sign", "prescribed_product": "Changed", "prescriber_signature": png_sig("x")})
        self.client.force_login(self.practitioner)
        self.client.post(reverse("forms_system:botox_operator", args=[done.pk]),
                         {"action": "sign", "units_forehead": "99", "operator_signature": png_sig("x")})

        done.refresh_from_db()
        self.assertEqual(done.prescribed_product, "Botox 100u")
        self.assertEqual(done.units_forehead, "10")
        self.assertEqual(done.revisions.count(), revisions)

        # Edit pages send you to the read-only record.
        self.assertRedirects(self.client.get(reverse("forms_system:botox_operator", args=[done.pk])),
                             reverse("forms_system:botox_view", args=[done.pk]))

    def test_next_submission_starts_a_new_form(self):
        self.client_submits()
        self.prescriber_saves()
        self.practitioner_saves()
        self.complete()

        self.client.force_login(self.client_user)
        page = self.client.get(reverse("forms_system:botox_client"))
        self.assertContains(page, "This is a new form")
        self.assertNotContains(page, "Update &amp; Sign")

        self.client_submits(current_medications="New answer")
        page = self.client.get(reverse("forms_system:botox_client"))
        self.assertContains(page, "New answer")  # in-progress answers are pre-filled
        self.assertContains(page, "Update &amp; Sign")

        forms = BotoxConsentForm.objects.filter(user=self.client_user).order_by("completed_at")
        self.assertEqual(forms.count(), 2)
        self.assertEqual(forms[0].current_medications, "None")  # completed record untouched
        self.assertTrue(forms[0].finalised)
        self.assertFalse(forms[1].finalised)

    def test_client_change_withdraws_prescriber_signature(self):
        self.client_submits()
        self.prescriber_saves()
        self.client_submits(current_medications="Warfarin")

        f = self.form()
        self.assertFalse(f.prescriber_signed)
        self.assertEqual(f.prescribed_product, "Botox 100u")  # their entries stay, just unsigned
        self.assertEqual(f.revisions.last().action, Action.SIGNATURE_WITHDRAWN)
        self.assertFalse(f.can_finalise)

        self.client.force_login(self.prescriber)
        page = self.client.get(reverse("forms_system:botox_prescriber", args=[f.pk]))
        self.assertContains(page, "changed their answers")

    def test_missing_signature_reshows_form_with_answers(self):
        r = self.client_submits(signature="", current_medications="Aspirin")
        self.assertEqual(r.status_code, 400)
        self.assertContains(r, "signature didn&#x27;t come through", status_code=400)
        self.assertContains(r, "Aspirin", status_code=400)              # nothing they typed is lost
        self.assertContains(r, "Submit Client Section", status_code=400)  # still a new form
        self.assertFalse(BotoxConsentForm.objects.filter(user=self.client_user).exists())

    def test_client_resigning_same_answers_keeps_prescriber_signature(self):
        self.client_submits()
        self.prescriber_saves()
        self.client_submits()
        self.assertTrue(self.form().prescriber_signed)

    def test_saves_only_touch_own_section(self):
        self.client_submits()
        self.practitioner_saves(action="save", units_forehead="12")
        self.prescriber_saves(action="save")
        f = self.form()
        self.assertEqual(f.units_forehead, "12")
        self.assertEqual(f.prescribed_product, "Botox 100u")
        self.assertFalse(f.prescriber_signed)

    def test_saving_progress_after_signing_removes_signature(self):
        self.client_submits()
        self.prescriber_saves()
        self.prescriber_saves(action="save", prescribed_dose="Up to 40 units")
        f = self.form()
        self.assertFalse(f.prescriber_signed)
        self.assertEqual(f.prescriber_signature, "")
        # The earlier signature is still in the history.
        signed = f.revisions.filter(action=Action.SIGNED).first()
        self.assertTrue(signed.data["prescriber_signature"].startswith("data:image/png"))

    def test_not_prescribed_can_be_completed_without_treatment(self):
        self.client_submits()
        self.prescriber_saves(prescription_decision="not_suitable", prescribed_product="", prescribed_dose="")
        self.assertTrue(self.form().can_finalise)
        self.complete()
        self.assertTrue(BotoxConsentForm.objects.get(user=self.client_user).finalised)

    def test_cannot_complete_before_prescriber_signs(self):
        self.client_submits()
        self.practitioner_saves()
        self.complete()
        self.assertFalse(self.form().finalised)

    def withdraw(self, user=None, **overrides):
        self.client.force_login(user or self.practitioner)
        data = {"action": "withdraw", "withdrawn_reason": "No appointment booked", "confirm_withdraw": "1"}
        data.update(overrides)
        return self.client.post(reverse("forms_system:botox_operator", args=[self.form().pk]), data)

    def test_withdraw_closes_form_but_keeps_it(self):
        self.client_submits()
        r = self.withdraw()
        f = self.form()
        self.assertRedirects(r, reverse("forms_system:botox_view", args=[f.pk]))
        self.assertTrue(f.withdrawn)
        self.assertTrue(f.is_closed)
        self.assertEqual(f.withdrawn_reason, "No appointment booked")
        self.assertEqual(f.withdrawn_by, self.practitioner)
        self.assertEqual(f.revisions.last().action, Action.WITHDRAWN)
        self.assertEqual(f.current_medications, "None")  # answers kept on file

        # Read-only from then on, for everyone.
        self.prescriber_saves()
        self.practitioner_saves()
        f.refresh_from_db()
        self.assertFalse(f.prescriber_signed)
        self.assertFalse(f.operator_signed)

        page = self.client.get(reverse("forms_system:botox_view", args=[f.pk]))
        self.assertContains(page, "Withdrawn")
        self.assertContains(page, "No appointment booked")

    def test_withdraw_needs_reason_and_confirmation(self):
        self.client_submits()
        self.withdraw(withdrawn_reason="")
        self.withdraw(confirm_withdraw="")
        self.assertFalse(self.form().withdrawn)

    def test_only_practitioner_can_withdraw(self):
        self.client_submits()
        self.withdraw(user=self.prescriber)
        self.assertFalse(self.form().withdrawn)

    def test_client_starts_fresh_after_withdrawal(self):
        self.client_submits()
        self.withdraw()
        self.client_submits(current_medications="New answer")
        forms = BotoxConsentForm.objects.filter(user=self.client_user).order_by("completed_at")
        self.assertEqual(forms.count(), 2)
        self.assertTrue(forms[0].withdrawn)
        self.assertEqual(forms[0].current_medications, "None")
        self.assertFalse(forms[1].is_closed)

    def test_prescriber_cannot_complete(self):
        self.client_submits()
        self.prescriber_saves()
        self.practitioner_saves()
        self.client.force_login(self.prescriber)
        self.client.post(reverse("forms_system:botox_operator", args=[self.form().pk]),
                         {"action": "complete", "confirm_complete": "1"})
        self.assertFalse(self.form().finalised)
