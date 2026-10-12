import base64
from datetime import date

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import PrescriberDetails, User
from apps.forms_system.models import (
    BotoxConsentForm, ConsultationForm, FormRevision, LaserReConsent,
    PhotographyConsent, PRPConsentForm, RecordCard,
)

Action  = FormRevision.Action
Section = FormRevision.Section


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


# ---------------------------------------------------------------------------
# Every form follows the shared lifecycle. These run once per form type.
# ---------------------------------------------------------------------------

class _LifecycleCases:
    model              = None
    client_url_name    = None
    signature_field    = "signature"
    answer_field       = None  # a free-text client field to change
    practitioner_field = None  # a free-text practitioner field
    practitioner_extra = {}    # other required practitioner fields

    @classmethod
    def setUpTestData(cls):
        cls.practitioner = User.objects.create_superuser(email="owner@example.com", password="x" * 12)
        cls.client_user  = User.objects.create_user(email="client@example.com", password="x" * 12, first_name="Amy")
        cls.prescriber   = User.objects.create_user(email="dr@example.com", password="x" * 12, role=User.Role.PRESCRIBER)

    # ---- helpers ----

    def client_data(self, **overrides):
        data = {"full_name": "Amy", "date_of_birth": "1990-01-01", "email": "client@example.com",
                self.answer_field: "first answer", self.signature_field: png_sig("client")}
        data.update(overrides)
        return data

    def client_submits(self, **overrides):
        self.client.force_login(self.client_user)
        return self.client.post(reverse(self.client_url_name), self.client_data(**overrides))

    def practitioner_posts(self, action, **overrides):
        self.client.force_login(self.practitioner)
        data = {"action": action, self.practitioner_field: "practitioner note", "operator_signature": png_sig("op"),
                **self.practitioner_extra}
        if action == "complete":
            data["confirm_complete"] = "1"
        if action == "withdraw":
            data.update(withdrawn_reason="No appointment booked", confirm_withdraw="1")
        data.update(overrides)
        return self.client.post(self.form().operator_url, data)

    def form(self):
        return self.model.objects.filter(user=self.client_user).latest("pk")

    # ---- tests ----

    def test_client_updates_same_open_form(self):
        self.client_submits()
        self.client_submits(**{self.answer_field: "second answer"})
        self.assertEqual(self.model.objects.filter(user=self.client_user).count(), 1)
        f = self.form()
        self.assertEqual(getattr(f, self.answer_field), "second answer")
        self.assertEqual([r.action for r in f.revisions.all()], [Action.SUBMITTED, Action.UPDATED])
        self.assertEqual(f.revisions.first().data[self.answer_field], "first answer")  # history kept

    def test_full_lifecycle_and_lock(self):
        self.client_submits()
        self.client.force_login(self.practitioner)
        self.assertEqual(self.client.get(self.form().operator_url).status_code, 200)

        self.practitioner_posts("save")
        f = self.form()
        self.assertEqual(getattr(f, self.practitioner_field), "practitioner note")
        self.assertFalse(f.operator_signed)
        self.assertFalse(f.can_finalise)

        self.practitioner_posts("sign")
        self.assertTrue(self.form().operator_signed)

        r = self.practitioner_posts("complete")
        f = self.form()
        self.assertTrue(f.finalised)
        self.assertRedirects(r, f.view_url, fetch_redirect_response=False)
        self.assertEqual(self.client.get(f.view_url).status_code, 200)
        self.assertEqual(f.revisions.last().action, Action.COMPLETED)

        # Locked: the practitioner can't change it, and edit pages redirect to the record.
        self.practitioner_posts("sign", **{self.practitioner_field: "changed"})
        self.assertEqual(getattr(self.form(), self.practitioner_field), "practitioner note")
        self.assertEqual(self.client.get(f.operator_url).status_code, 302)

        # The client's next submission starts a fresh form; the completed one is untouched.
        self.client_submits(**{self.answer_field: "next visit"})
        forms = self.model.objects.filter(user=self.client_user).order_by("pk")
        self.assertEqual(forms.count(), 2)
        self.assertEqual(getattr(forms[0], self.answer_field), "first answer")
        self.assertFalse(forms[1].is_closed)

    def test_client_change_withdraws_practitioner_signature(self):
        self.client_submits()
        self.practitioner_posts("sign")
        self.client_submits(**{self.answer_field: "changed answer"})
        f = self.form()
        self.assertFalse(f.operator_signed)
        self.assertEqual(f.revisions.filter(section=Section.OPERATOR).last().action, Action.SIGNATURE_WITHDRAWN)
        self.client.force_login(self.practitioner)
        self.assertContains(self.client.get(f.operator_url), "client changed their answers after you signed")

    def test_cannot_complete_before_signing(self):
        self.client_submits()
        self.practitioner_posts("complete")
        self.assertFalse(self.form().finalised)

    def test_withdraw(self):
        self.client_submits()
        self.practitioner_posts("withdraw")
        f = self.form()
        self.assertTrue(f.withdrawn)
        self.client.force_login(self.practitioner)
        self.assertContains(self.client.get(f.view_url), "Withdrawn")

    def test_only_practitioner_can_use_practitioner_page(self):
        self.client_submits()
        for user in (self.client_user, self.prescriber):
            self.client.force_login(user)
            self.client.post(self.form().operator_url, {"action": "sign", "operator_signature": png_sig("x")})
        self.assertFalse(self.form().operator_signed)

    def test_practitioner_on_behalf_goes_to_practitioner_page(self):
        self.client.force_login(self.practitioner)
        url = reverse(self.client_url_name) + f"?on_behalf_of={self.client_user.pk}"
        r = self.client.post(url, self.client_data(**{self.answer_field: "via practitioner"}))
        self.assertRedirects(r, self.form().operator_url, fetch_redirect_response=False)

    def test_client_page_prefills_open_form(self):
        self.client_submits(**{self.answer_field: "remember me"})
        page = self.client.get(reverse(self.client_url_name))
        self.assertContains(page, "remember me")
        self.assertContains(page, "Update &amp; Sign")


class ConsultationLifecycleTests(_LifecycleCases, TestCase):
    model, client_url_name = ConsultationForm, "forms_system:consultation"
    answer_field, practitioner_field = "current_medications", "pretx_comments"


class PhotographyLifecycleTests(_LifecycleCases, TestCase):
    model, client_url_name = PhotographyConsent, "forms_system:photography"
    answer_field, practitioner_field = "address", "operator_notes"


class PRPLifecycleTests(_LifecycleCases, TestCase):
    model, client_url_name = PRPConsentForm, "forms_system:prp_client"
    answer_field, practitioner_field = "current_medications", "operator_notes"


class RecordCardReConsentLifecycleTests(_LifecycleCases, TestCase):
    """The client's re-consent (on their own device) is the record card's client section."""
    model, client_url_name = RecordCard, "forms_system:laser_reconsent"
    signature_field = "reconsent_signature"
    answer_field, practitioner_field = "changes_detail", "operator_comments"
    practitioner_extra = {"date": "2026-10-01", "time": "10:30"}

    def client_data(self, **overrides):
        return super().client_data(consent_proceed="on", **overrides)


class RecordCardLifecycleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.practitioner = User.objects.create_superuser(email="owner@example.com", password="x" * 12)
        cls.client_user  = User.objects.create_user(email="client@example.com", password="x" * 12, first_name="Amy")

    def setUp(self):
        self.client.force_login(self.practitioner)

    def card_data(self, **overrides):
        data = {"date": "2026-10-01", "time": "10:30", "treatment_for": "Hair removal", "area_1": "Legs",
                "consent_proceed": "on", "client_feedback": "No issues",
                "reconsent_signature": png_sig("client"), "operator_signature": png_sig("op"), "action": "save"}
        data.update(overrides)
        return data

    def client_reconsents(self, **overrides):
        self.client.force_login(self.client_user)
        data = {"consent_proceed": "on", "client_feedback": "Skin fine", "reconsent_signature": png_sig("client")}
        data.update(overrides)
        r = self.client.post(reverse("forms_system:laser_reconsent"), data)
        self.client.force_login(self.practitioner)
        return r

    def test_client_reconsent_then_practitioner_completes_same_card(self):
        from apps.dashboard.models import Notification
        self.client_reconsents()
        card = RecordCard.objects.get(user=self.client_user)
        self.assertEqual((card.client_feedback, card.date), ("Skin fine", date.today()))
        self.assertTrue(Notification.objects.filter(form_type="record_card", form_id=card.pk).exists())

        # Starting a new card picks up the one the client began.
        new_url = reverse("forms_system:record_card_new", args=[self.client_user.pk])
        self.assertRedirects(self.client.get(new_url), card.operator_url, fetch_redirect_response=False)
        page = self.client.get(card.operator_url)
        self.assertContains(page, "Skin fine")
        self.assertNotContains(page, 'id="reconsentSigCanvas"')  # already signed — shown read-only

        # The practitioner's save can't change the client's section.
        self.client.post(card.operator_url, self.card_data(client_feedback="overwritten", action="sign"))
        self.client.post(card.operator_url, {"action": "complete", "confirm_complete": "1"})
        card.refresh_from_db()
        self.assertEqual((card.client_feedback, card.area_1), ("Skin fine", "Legs"))
        self.assertTrue(card.finalised)
        self.assertEqual(RecordCard.objects.filter(user=self.client_user).count(), 1)

        # The client's next re-consent starts the next card.
        self.client_reconsents()
        self.assertEqual(list(RecordCard.objects.filter(user=self.client_user).order_by("pk")
                              .values_list("treatment_number", "finalised")), [(1, True), (2, False)])

    def test_reconsent_taken_on_practitioner_page_is_logged_as_client_section(self):
        self.client.post(reverse("forms_system:record_card_new", args=[self.client_user.pk]), self.card_data())
        card = RecordCard.objects.get(user=self.client_user)
        self.assertTrue(card.consent_proceed)
        self.assertEqual(
            list(card.revisions.values_list("section", "action")),
            [(Section.OPERATOR, Action.SAVED), (Section.CLIENT, Action.SUBMITTED)],
        )
        from apps.dashboard.models import Notification
        self.assertFalse(Notification.objects.filter(form_type="record_card").exists())  # practitioner started it

    def test_reconsent_needs_declaration_before_signing(self):
        r = self.client.post(reverse("forms_system:record_card_new", args=[self.client_user.pk]),
                             self.card_data(consent_proceed=""))
        self.assertContains(r, "must tick the re-consent declaration")
        self.assertFalse(RecordCard.objects.exists())

    def test_answers_saved_before_client_signs(self):
        self.client.post(reverse("forms_system:record_card_new", args=[self.client_user.pk]),
                         self.card_data(reconsent_signature="", consent_proceed=""))
        card = RecordCard.objects.get(user=self.client_user)
        self.assertEqual(card.client_feedback, "No issues")
        self.assertFalse(card.client_section_done)
        self.assertEqual(card.revisions.filter(section=Section.CLIENT).get().action, Action.SAVED)

        # The client can then sign the same card on their own device.
        self.client_reconsents(client_feedback="Signed at home")
        card.refresh_from_db()
        self.assertTrue(card.client_section_done)
        self.assertEqual(RecordCard.objects.filter(user=self.client_user).count(), 1)

    def test_archived_reconsent_still_viewable(self):
        old = LaserReConsent.objects.create(user=self.client_user, client_signature=png_sig("c"), finalised=True)
        self.assertEqual(self.client.get(old.view_url).status_code, 200)
        self.assertRedirects(self.client.get(old.operator_url), old.view_url, fetch_redirect_response=False)

    def test_draft_then_sign_then_complete(self):
        new_url = reverse("forms_system:record_card_new", args=[self.client_user.pk])
        self.assertEqual(self.client.get(new_url).status_code, 200)

        r = self.client.post(new_url, self.card_data())
        card = RecordCard.objects.get(user=self.client_user)
        self.assertRedirects(r, card.operator_url, fetch_redirect_response=False)
        self.assertEqual(card.treatment_number, 1)
        self.assertEqual(card.area_1, "Legs")
        self.assertTrue(card.reconsent_signature)
        self.assertFalse(card.operator_signed)

        # Edit the draft — the client's signature is kept unless re-drawn.
        self.assertContains(self.client.get(card.operator_url), 'value="Legs"')
        self.client.post(card.operator_url, self.card_data(area_1="Arms", reconsent_signature="", action="sign"))
        card.refresh_from_db()
        self.assertEqual(card.area_1, "Arms")
        self.assertTrue(card.reconsent_signature)
        self.assertTrue(card.operator_signed)

        self.client.post(card.operator_url, {"action": "complete", "confirm_complete": "1"})
        card.refresh_from_db()
        self.assertTrue(card.finalised)
        self.assertEqual(self.client.get(card.view_url).status_code, 200)

        self.client.post(card.operator_url, self.card_data(area_1="Face", action="sign"))
        card.refresh_from_db()
        self.assertEqual(card.area_1, "Arms")

    def test_cannot_complete_without_client_reconsent(self):
        self.client.post(reverse("forms_system:record_card_new", args=[self.client_user.pk]),
                         self.card_data(reconsent_signature="", action="sign"))
        card = RecordCard.objects.get(user=self.client_user)
        self.assertTrue(card.operator_signed)
        self.client.post(card.operator_url, {"action": "complete", "confirm_complete": "1"})
        card.refresh_from_db()
        self.assertFalse(card.finalised)


class NewFormStartsFromLastTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.practitioner = User.objects.create_superuser(email="owner@example.com", password="x" * 12)
        cls.client_user  = User.objects.create_user(email="client@example.com", password="x" * 12, first_name="Amy")

    def complete(self, model, url_name, sig_field="signature", **answers):
        self.client.force_login(self.client_user)
        data = {"full_name": "Amy", "date_of_birth": "1990-01-01", "email": "client@example.com",
                sig_field: png_sig("client"), **answers}
        self.client.post(reverse(url_name), data)
        form = model.objects.filter(user=self.client_user).latest("pk")
        self.client.force_login(self.practitioner)
        self.client.post(form.operator_url, {"action": "sign", "operator_signature": png_sig("op")})
        self.client.post(form.operator_url, {"action": "complete", "confirm_complete": "1"})
        form.refresh_from_db()
        self.assertTrue(form.finalised)
        self.client.force_login(self.client_user)

    def test_new_consultation_prefills_answers_but_not_consents(self):
        self.complete(ConsultationForm, "forms_system:consultation",
                      current_medications="Vitamin D", consent_certified="on")
        page = self.client.get(reverse("forms_system:consultation"))
        self.assertContains(page, "Vitamin D")
        self.assertContains(page, "tick each consent again")
        self.assertContains(page, 'name="consent_certified" required >')  # unticked
        self.assertNotContains(page, "Update &amp; Sign")

    def test_photography_shows_consent_on_file_with_update_option(self):
        self.complete(PhotographyConsent, "forms_system:photography", consent_1="on")
        page = self.client.get(reverse("forms_system:photography"))
        self.assertContains(page, "Consent on file")
        self.assertContains(page, "Update consent")

        page = self.client.get(reverse("forms_system:photography") + "?new=1")
        self.assertNotContains(page, "Consent on file")
        self.assertContains(page, 'id="photographyForm"')


class PractitionerWorklistTests(TestCase):
    """The practitioner's 'Forms awaiting you' list on their profile page."""

    @classmethod
    def setUpTestData(cls):
        cls.practitioner = User.objects.create_superuser(email="owner@example.com", password="x" * 12)

    def setUp(self):
        self.client.force_login(self.practitioner)

    def make_client(self, name):
        return User.objects.create_user(email=f"{name.lower()}@example.com", password="x" * 12, first_name=name)

    def submit(self, user, model=PRPConsentForm, **fields):
        defaults = dict(user=user, signature=png_sig("c"), full_name=user.first_name,
                        date_of_birth=date(1990, 1, 1), email=user.email, client_signed=True)
        defaults.update(fields)
        return model.objects.create(**defaults)

    def book(self, user, when):
        from apps.bookings.models import Booking
        from apps.treatments.models import Treatment, TreatmentCategory
        cat, _ = TreatmentCategory.objects.get_or_create(name="Injectables")
        tx, _  = Treatment.objects.get_or_create(name="PRP", category=cat, defaults={"duration_minutes": 30, "price": 100})
        Booking.objects.create(user=user, treatment=tx, date=when, start_time="23:00")

    def lists(self):
        ctx = self.client.get(reverse("accounts:profile")).context
        return [f.pk for f in ctx["awaiting"]], [f.pk for f in ctx["unbooked"]]

    def test_shows_forms_needing_practitioner_split_by_appointment(self):
        booked   = self.submit(self.make_client("Booked"))
        unbooked = self.submit(self.make_client("Unbooked"))
        self.book(booked.user, date.today())

        self.submit(self.make_client("Done"), finalised=True)
        self.submit(self.make_client("Gone"), withdrawn=True)
        self.submit(self.make_client("NotYet"), client_signed=False)

        self.assertEqual(self.lists(), ([booked.pk], [unbooked.pk]))

    def test_includes_every_form_type(self):
        user = self.make_client("Amy")
        self.book(user, date.today())
        self.submit(user)  # PRP
        PhotographyConsent.objects.create(user=user, signature=png_sig("c"), full_name="Amy", date_of_birth=date(1990, 1, 1))
        RecordCard.objects.create(user=user, date=date.today(), time="10:00")

        page = self.client.get(reverse("accounts:profile"))
        titles = sorted(f.FORM_TITLE for f in page.context["awaiting"])
        self.assertEqual(titles, ["PRP Consent", "Photography Consent", "Record Card"])
        self.assertContains(page, "Forms Awaiting You")
        self.assertNotContains(page, "My Forms")

    def test_signed_form_shows_as_ready_to_complete(self):
        f = self.submit(self.make_client("Ready"), operator_signed=True, operator_signature=png_sig("op"))
        unbooked = self.client.get(reverse("accounts:profile")).context["unbooked"]
        self.assertEqual([(x.pk, x.worklist_status) for x in unbooked], [(f.pk, "ready")])

    def test_botox_waiting_only_on_prescriber_is_left_out(self):
        user = self.make_client("Bo")
        BotoxConsentForm.objects.create(
            user=user, signature=png_sig("c"), full_name="Bo", date_of_birth=date(1990, 1, 1),
            email=user.email, client_signed=True, operator_signed=True, operator_signature=png_sig("op"),
        )
        self.assertEqual(self.lists(), ([], []))

    def test_clients_still_see_their_own_forms(self):
        user = self.make_client("Client")
        self.client.force_login(user)
        page = self.client.get(reverse("accounts:profile"))
        self.assertContains(page, "My Forms")
        self.assertNotIn("awaiting", page.context)
