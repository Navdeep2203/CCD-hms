import { useState } from "react";
import { api } from "./api/client";
import { useAuth } from "./auth/AuthContext";
import { useAction } from "./hooks/useAction";
import { HOTEL_NAME } from "./nav";

export default function ChangePassword() {
  const { refreshUser } = useAuth();

  const [form, setForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });

  const { run, busy } = useAction(async () => {
    if (form.new_password !== form.confirm_password) {
      throw new Error("New password and confirmation do not match");
    }

    await api.post("/auth/change-password", {
      current_password: form.current_password,
      new_password: form.new_password,
    });

    await refreshUser();
  });

  async function submit(event) {
    event.preventDefault();
    await run();
  }

  return (
    <main className="authPage">
      <section className="authVisual">
        <div className="authCopy">
          <div className="brandLockup">
            <div className="brandMark large">MH</div>
            <span>{HOTEL_NAME}</span>
          </div>

          <p className="eyebrow">ACCOUNT SECURITY</p>

          <h1>Set your new password.</h1>

          <p>
            Your account is using a temporary password. Choose a new password
            before continuing to the hotel workspace.
          </p>
        </div>
      </section>

      <section className="authPanel">
        <div className="authCardHead">
          <div className="brandMark">MH</div>

          <div>
            <strong>{HOTEL_NAME} HMS</strong>
            <span>Hotel operations console</span>
          </div>
        </div>

        <h2>Change password</h2>

        <form onSubmit={submit} className="form">
          <label>
            Current password
            <input
              type="password"
              value={form.current_password}
              onChange={(e) =>
                setForm({
                  ...form,
                  current_password: e.target.value,
                })
              }
              required
            />
          </label>

          <label>
            New password
            <input
              type="password"
              value={form.new_password}
              onChange={(e) =>
                setForm({
                  ...form,
                  new_password: e.target.value,
                })
              }
              minLength={8}
              pattern="(?=.*[A-Za-z])(?=.*\d).{8,72}"
              required
            />
            <small className="fieldHint">
              At least 8 characters with a letter and a digit.
            </small>
          </label>

          <label>
            Confirm new password
            <input
              type="password"
              value={form.confirm_password}
              onChange={(e) =>
                setForm({
                  ...form,
                  confirm_password: e.target.value,
                })
              }
              required
            />
          </label>

          <button className="primary" disabled={busy}>
            {busy ? "Updating..." : "Change password"}
          </button>
        </form>
      </section>
    </main>
  );
}
