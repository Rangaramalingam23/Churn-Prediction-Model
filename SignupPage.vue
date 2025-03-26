<template>
  <div class="auth-wrapper">
    <TopBar />
    <div class="auth-content">
      <!-- Image Card (Left Side) -->
      <div class="image-container">
        <img :src="require('@/assets/gepnic.jpg')"  alt="GEPNIC" class="info-image" />
        <img :src="require('@/assets/digitalindia.jpg')" alt="Digital India" class="info-image" />
      </div>

      <!-- Login Form Card (Right Side) -->
      <div class="auth-box">
        <h2 class="auth-title">Login</h2>
        <p class="auth-instruction">Enter your credentials to continue</p>

        <form @submit.prevent="authenticate">
          <!-- Email Field -->
          <div class="form-group" v-if="!show2FA">
            <label>Email</label>
            <input type="text" v-model="email" required class="form-control" />
          </div>

          <!-- Password Field with Eye Icon -->
          <div class="form-group" v-if="!show2FA">
            <label>Password</label>
            <div class="password-wrapper">
              <input
                :type="showPassword ? 'text' : 'password'"
                v-model="password"
                required
                class="form-control"
              />
              <span class="eye-icon" @click="togglePasswordVisibility">
                <i :class="showPassword ? 'fas fa-eye-slash' : 'fas fa-eye'"></i>
              </span>
            </div>
          </div>

          <!-- 2FA OTP Field -->
          <div v-if="show2FA" class="form-group">
            <label>Enter 2FA Code</label>
            <input
              type="text"
              v-model="twoFACode"
              required
              class="form-control"
              placeholder="Enter OTP"
            />
          </div>

          <!-- Login Button -->
          <button type="submit" class="btn btn-primary">
            {{ show2FA ? "Verify OTP" : "Login" }}
          </button>
        </form>

        <!-- Reset Password Section (Shown only if pwdChanged is false) -->
        <div v-if="!show2FA && pwdChanged === false">
          <button
            v-if="!showResetPassword"
            @click="showResetPassword = true"
            class="btn btn-secondary mt-3"
          >
            Reset Password
          </button>

          <!-- Reset Password Form -->
          <div v-if="showResetPassword" class="form-group">
            <label>Old Password</label>
            <input
              type="password"
              v-model="oldPassword"
              required
              class="form-control"
              placeholder="Enter old password"
            />

            <label>New Password</label>
            <input
              type="password"
              v-model="newPassword"
              required
              class="form-control"
              placeholder="Enter new password"
            />

            <button @click="resetPassword" class="btn btn-primary mt-2">Submit</button>
            <button
              @click="showResetPassword = false"
              class="btn btn-secondary mt-2"
            >
              Cancel
            </button>
          </div>
        </div>

        <!-- Forgot Password Section (Always Visible) -->
        <div>
          <button
            v-if="!showForgotPassword"
            @click="showForgotPassword = true"
            class="btn btn-secondary mt-3"
          >
            Forgot Password
          </button>

          <!-- Forgot Password Form -->
          <div v-if="showForgotPassword" class="form-group">
            <label>Email</label>
            <input
              type="text"
              v-model="forgotEmail"
              required
              class="form-control"
              placeholder="Enter your email"
            />

            <label>2FA Code</label>
            <input
              type="text"
              v-model="twoFACodeForReset"
              required
              class="form-control"
              placeholder="Enter 2FA Code"
            />

            <label>New Password</label>
            <input
              type="password"
              v-model="newPassword"
              required
              class="form-control"
              placeholder="Enter new password"
            />

            <button @click="forgotPassword" class="btn btn-primary mt-2">Submit</button>
            <button
              @click="showForgotPassword = false"
              class="btn btn-secondary mt-2"
            >
              Cancel
            </button>
          </div>
        </div>

        <!-- Error Message and Reject Reason -->
        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
        <p v-if="rejectReason" class="reject-text">Reason: {{ rejectReason }}</p>

        <!-- Signup Link -->
        <div class="auth-footer">
          <p>
            New user?
            <a @click.prevent="goToSignup" class="signup-link">Create an account</a>
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from "axios";
import API_URL from "@/services/config.js";

export default {
  data() {
    return {
      email: "",
      password: "",
      twoFACode: "",
      show2FA: false,
      errorMessage: "",
      rejectReason: "",
      showResetPassword: false,
      newPassword: "",
      forgotEmail: "",
      showForgotPassword: false,
      twoFACodeForReset: "",
      oldPassword: "",
      pwdChanged: null, // Initially null until we get a response
      showPassword: false,
    };
  },
  methods: {
    goToSignup() {
      this.$emit("go-to-signup");
    },

    async resetPassword() {
      if (!this.oldPassword || !this.newPassword) {
        this.errorMessage = "Please enter the old password and new password!";
        return;
      }

      const payload = {
        email: this.email,
        oldPassword: this.oldPassword,
        newPassword: this.newPassword,
      };

      try {
        const response = await axios.post(`${API_URL}/reset-password`, payload);
        const qrCodeUrl = `data:image/png;base64,${response.data.qr_code}`;
        const qrCodeWindow = window.open("");
        qrCodeWindow.document.write(`<img src="${qrCodeUrl}" alt="QR Code" />`);
        alert(response.data.message);
        this.showResetPassword = false;
        this.oldPassword = "";
        this.newPassword = "";
        this.errorMessage = "";
        this.pwdChanged = true; // Update pwdChanged after successful reset
      } catch (error) {
        console.error("Error in resetPassword:", error.response);
        this.errorMessage =
          error.response?.data?.message || "Password reset failed!";
      }
    },

    async forgotPassword() {
      if (!this.forgotEmail || !this.newPassword || !this.twoFACodeForReset) {
        this.errorMessage = "Please enter email, new password, and 2FA code!";
        return;
      }
      try {
        const response = await axios.post(`${API_URL}/forgot-password`, {
          email: this.forgotEmail,
          new_password: this.newPassword,
          otp_code: this.twoFACodeForReset,
        });
        console.log("Forgot Password Response:", response.data);
        alert(response.data.message);
        this.showForgotPassword = false;
        this.forgotEmail = "";
        this.newPassword = "";
        this.twoFACodeForReset = "";
      } catch (error) {
        console.error("Forgot Password Error:", error.response);
        this.errorMessage =
          error.response?.data?.message ||
          "Failed to process forgot password request!";
      }
    },

    async authenticate() {
      this.errorMessage = "";
      this.rejectReason = "";

      if (!this.show2FA) {
        // Step 1: Validate credentials
        if (!this.email || !this.password) {
          this.errorMessage = "Please fill in all fields!";
          return;
        }

        try {
          const response = await axios.post(`${API_URL}/login`, {
            email: this.email,
            password: this.password,
          });

          if (response.data.message === "2FA Code required!") {
            this.show2FA = true;
            this.pwdChanged = response.data.pwdChanged; // Set pwdChanged from response
            return;
          } else if (
            response.data.message ===
            "You are using the default password. Please reset your password before logging in."
          ) {
            this.errorMessage = response.data.message;
            this.pwdChanged = false; // Explicitly set to false
            return;
          } else if (response.data.token) {
            this.pwdChanged = response.data.pwdChanged;
            localStorage.setItem("authToken", response.data.token);
            localStorage.setItem("refreshToken", response.data.refresh_token);
            localStorage.setItem("isAuthenticated", "true");
            localStorage.setItem("userRole", response.data.role);
            this.$emit("login-success");
            this.$router.push('/').catch(err => console.error("Router error:", err));
          } else {
            this.errorMessage = "Unexpected response from server!";
          }
        } catch (error) {
          if (
            error.response?.status === 400 &&
            error.response?.data?.message === "2FA Code required!"
          ) {
            this.show2FA = true;
            this.pwdChanged = error.response.data.pwdChanged; // Set pwdChanged from response
            return;
          }
          const data = error.response?.data || {};
          this.errorMessage = data.message || "Login failed!";
          if (data.reject_reason) {
            this.rejectReason = data.reject_reason;
          }
          if (
            data.message ===
            "You are using the default password. Please reset your password before logging in."
          ) {
            this.pwdChanged = false; // Set pwdChanged to false if default password is detected
          }
        }
      } else {
        // Step 2: Verify 2FA code
        if (!this.twoFACode) {
          this.errorMessage = "Please enter the 2FA code!";
          return;
        }

        try {
          const response = await axios.post(`${API_URL}/login`, {
            email: this.email,
            password: this.password,
            otp_code: this.twoFACode,
          });

          if (response.data.token) {
            localStorage.setItem("authToken", response.data.token);
            localStorage.setItem("refreshToken", response.data.refresh_token);
            localStorage.setItem("isAuthenticated", "true");
            localStorage.setItem("userRole", response.data.role);
            localStorage.setItem("userEmail", this.email);
            this.$emit("login-success");
            this.$router.push('/').catch(err => console.error("Router error:", err));
          } else {
            this.errorMessage = "Login failed: No token received!";
          }
        } catch (error) {
          const data = error.response?.data || {};
          this.errorMessage = data.message || "Invalid 2FA Code!";
          if (data.reject_reason) {
            this.rejectReason = data.reject_reason;
          }
        }
      }
    },

    togglePasswordVisibility() {
      this.showPassword = !this.showPassword;
    },
  },
};
</script>

<style scoped>
.auth-wrapper {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: linear-gradient(to bottom, #f5f7fa, #ffffff);
}

.signup-link {
  color: #007bff;
  text-decoration: underline;
  font-weight: bold;
  cursor: pointer;
}

.signup-link:hover {
  color: #007bff;
}

/* Top Bar */
.TopBar {
  background: rgba(0, 123, 255, 0.9);
  padding: 15px;
  text-align: center;
  color: white;
  font-size: 1.5rem;
  font-weight: bold;
}

.auth-content {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  gap: 30px;
  padding: 20px;
  flex-wrap: wrap; /* Ensures responsiveness */
}

.auth-box, .image-container {
  width: 400px;
  min-height: 450px;
  background: white;
  padding: 1.5rem;
  border-radius: 10px;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
  text-align: center;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.image-container {
  align-items: center;
  order: -1; /* Ensures image is on the left */
}

.info-image {
  width: 100%;
  height: auto;
  max-height: 200px;
  border-radius: 8px;
  margin-bottom: 10px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.auth-title {
  font-size: 1.8rem;
  font-weight: bold;
  margin-bottom: 5px;
}

.auth-instruction {
  font-size: 0.9rem;
  color: #666;
  margin-bottom: 15px;
}

.form-group {
  margin-bottom: 15px;
  text-align: left;
}

.form-control {
  width: 100%;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 5px;
}

/* Password Wrapper for Eye Icon */
.password-wrapper {
  position: relative;
}

.password-wrapper .form-control {
  padding-right: 40px; /* Make room for the eye icon */
}

.eye-icon {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  cursor: pointer;
  color: #666;
}

.eye-icon:hover {
  color: #007bff;
}

.btn {
  padding: 10px 15px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  margin: 5px 0; /* Prevents overlap */
  width: 100%; /* Makes it responsive */
}

.btn-primary {
  background: #007bff;
  color: white;
}

.btn-secondary {
  background: #6c757d;
  color: white;
}

.button-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.error-text {
  color: red;
  font-size: 0.9rem;
  margin-top: 10px;
}

/* Rejection Reason */
.reject-text {
  color: #dc3545; /* Slightly different red for distinction */
  font-size: 0.9rem;
  margin-top: 5px;
  font-weight: bold;
}

.auth-footer {
  margin-top: 10px;
  font-size: 0.9rem;
}

@media (max-width: 900px) {
  .auth-content {
    flex-direction: column; /* Stacks on small screens */
    gap: 20px;
  }

  .auth-box, .image-container {
    width: 90%;
    max-width: 400px;
  }
}
</style>
