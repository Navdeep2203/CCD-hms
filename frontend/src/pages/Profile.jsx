import { useEffect, useState } from "react";

import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { useAction } from "../hooks/useAction";
import { useToast } from "../components/Toast";
import Modal from "../components/Modal";
import PageHeader from "../components/PageHeader";

const EMPTY_PROFILE = {
  name: "",
  phone_country_code: "+91",
  phone_number: "",
  address: "",
  id_proof: "",
  nationality: "",
};

const EMPTY_PASSWORD = {
  current_password: "",
  new_password: "",
  confirm_password: "",
};

export default function Profile() {
  const { user, isGuest, refreshUser } = useAuth();
  const { notify } = useToast();

  const [profileForm, setProfileForm] = useState(EMPTY_PROFILE);
  const [passwordForm, setPasswordForm] = useState(EMPTY_PASSWORD);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [profileLoaded, setProfileLoaded] = useState(false);

  useEffect(() => {
    if (!user) return;

    setProfileForm({
      name: user.name || "",
      phone_country_code: user.phone_country_code || "+91",
      phone_number: user.phone_number || "",
      address: user.address || "",
      id_proof: user.id_proof || "",
      nationality: user.nationality || "",
    });
    setProfileLoaded(true);
  }, [user]);

  const { run: saveProfile, busy: profileBusy } = useAction(async () => {
    if (!profileForm.name.trim()) {
      notify("Name is required", "error");
      return null;
    }

    const payload = {
      name: profileForm.name.trim(),
      phone_country_code: profileForm.phone_country_code || null,
      phone_number: profileForm.phone_number || null,
    };

    if (isGuest) {
      payload.address = profileForm.address || null;
      payload.id_proof = profileForm.id_proof || null;
      payload.nationality = profileForm.nationality || null;
    }

    const result = await api.put("/auth/profile", payload);
    await refreshUser();
    notify("Profile updated successfully", "success");
    return result;
  });

  const { run: changePassword, busy: passwordBusy } = useAction(async () => {
    if (
      !passwordForm.current_password ||
      !passwordForm.new_password ||
      !passwordForm.confirm_password
    ) {
      notify("Fill in all password fields", "error");
      return null;
    }

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      notify("New passwords do not match", "error");
      return null;
    }

    if (
      passwordForm.new_password.length < 8 ||
      passwordForm.new_password.length > 72
    ) {
      notify("New password must be 8 to 72 characters", "error");
      return null;
    }

    if (
      !/[A-Za-z]/.test(passwordForm.new_password) ||
      !/\d/.test(passwordForm.new_password)
    ) {
      notify(
        "New password must contain at least one letter and one digit",
        "error",
      );
      return null;
    }

    const result = await api.post("/auth/change-password", {
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password,
    });

    await refreshUser();
    notify("Password changed successfully", "success");
    setPasswordForm(EMPTY_PASSWORD);
    setPasswordModalOpen(false);
    return result;
  });

  if (!user || !profileLoaded) {
    return (
      <section className="workspace">
        <div className="panel wide">
          <p className="muted">Loading profile...</p>
        </div>
      </section>
    );
  }

  return (
    <section className="workspace">
      <PageHeader
        eyebrow="Account"
        title="Profile"
        subtitle="Manage your personal details, address information, and security password."
        secondaryActions={<span>{user.email}</span>}
        primaryAction={
          <button
            type="button"
            className="secondary"
            onClick={() => {
              setPasswordForm(EMPTY_PASSWORD);
              setPasswordModalOpen(true);
            }}
          >
            Change password
          </button>
        }
      />

      <div className="panel wide">

        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            saveProfile();
          }}
        >
          <label>
            Name
            <input
              value={profileForm.name}
              onChange={(event) =>
                setProfileForm((current) => ({
                  ...current,
                  name: event.target.value,
                }))
              }
              required
            />
          </label>

          <label>
            Email
            <input value={user.email || ""} disabled />
          </label>

          <label>
            Phone country code
            <input
              value={profileForm.phone_country_code}
              onChange={(event) =>
                setProfileForm((current) => ({
                  ...current,
                  phone_country_code: event.target.value,
                }))
              }
            />
          </label>

          <label>
            Phone number
            <input
              value={profileForm.phone_number}
              onChange={(event) =>
                setProfileForm((current) => ({
                  ...current,
                  phone_number: event.target.value,
                }))
              }
            />
          </label>

          {isGuest && (
            <>
              <label>
                Address
                <textarea
                  rows="3"
                  maxLength="255"
                  value={profileForm.address}
                  onChange={(event) =>
                    setProfileForm((current) => ({
                      ...current,
                      address: event.target.value,
                    }))
                  }
                />
              </label>

              <label>
                ID proof
                <input
                  maxLength="100"
                  value={profileForm.id_proof}
                  onChange={(event) =>
                    setProfileForm((current) => ({
                      ...current,
                      id_proof: event.target.value,
                    }))
                  }
                />
              </label>

              <label>
                Nationality
                <input
                  maxLength="50"
                  value={profileForm.nationality}
                  onChange={(event) =>
                    setProfileForm((current) => ({
                      ...current,
                      nationality: event.target.value,
                    }))
                  }
                />
              </label>

              <div className="statsGrid">
                <div className="statCard">
                  <span>Loyalty points</span>
                  <strong>{user.loyalty_points ?? 0}</strong>
                </div>
              </div>
            </>
          )}

          <button type="submit" className="primary" disabled={profileBusy}>
            {profileBusy ? "Saving..." : "Save profile"}
          </button>
        </form>
      </div>

      <Modal
        open={passwordModalOpen}
        title="Change password"
        onClose={() => {
          if (!passwordBusy) {
            setPasswordModalOpen(false);
            setPasswordForm(EMPTY_PASSWORD);
          }
        }}
      >
        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            changePassword();
          }}
        >
          <label>
            Current password
            <input
              type="password"
              value={passwordForm.current_password}
              onChange={(event) =>
                setPasswordForm((current) => ({
                  ...current,
                  current_password: event.target.value,
                }))
              }
              autoComplete="current-password"
              required
            />
          </label>

          <label>
            New password
            <input
              type="password"
              minLength="8"
              maxLength="72"
              value={passwordForm.new_password}
              onChange={(event) =>
                setPasswordForm((current) => ({
                  ...current,
                  new_password: event.target.value,
                }))
              }
              autoComplete="new-password"
              required
            />
          </label>

          <label>
            Confirm new password
            <input
              type="password"
              minLength="8"
              maxLength="72"
              value={passwordForm.confirm_password}
              onChange={(event) =>
                setPasswordForm((current) => ({
                  ...current,
                  confirm_password: event.target.value,
                }))
              }
              autoComplete="new-password"
              required
            />
          </label>

          <button type="submit" className="primary" disabled={passwordBusy}>
            {passwordBusy ? "Changing..." : "Change password"}
          </button>
        </form>
      </Modal>
    </section>
  );
}
