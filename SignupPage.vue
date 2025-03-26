<template>
  <div class="auth-wrapper">
    <div class="auth-content">
      <!-- Image Card (Left Side) -->
      <div class="image-container">
        <img :src="require('@/assets/gepnic-logo.jpg')" alt="GEPNIC" class="info-image" />
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

          <!-- Password Field -->
          <div class="form-group" v-if="!show2FA">
            <label>Password</label>
            <input type="password" v-model="password" required class="form-control" />
          </div>

          <!-- Role Selection -->
          <div class="form-group" v-if="!show2FA">
            <label>Select Role</label>
            <select v-model="selectedRole" required class="form-control">
              <option value="">Choose Role</option>
              <option value="admin">Admin</option>
              <option value="user">User</option>
            </select>
          </div>

          <!-- Location Field -->
          <div class="form-group" v-if="!show2FA">
            <label>Location</label>
            <input
              type="text"
              v-model="location"
              required
              class="form-control"
              placeholder="Enter your location"
            />
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
          <button type="submit" class="btn btn-primary">{{ show2FA ? "Verify OTP" : "Login" }}</button>
        </form>

        <!-- Reset Password Section (Admin Only) -->
        <div v-if="selectedRole === 'admin' && !show2FA && !pwdChanged">
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
            <button @click="showResetPassword = false" class="btn btn-secondary mt-2">Cancel</button>
          </div>
        </div>

        <!-- Forgot Password Section (Admin and User) -->
        <div v-if="(selectedRole === 'admin' && pwdChanged) || selectedRole === 'user'">
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
            <button @click="showForgotPassword = false" class="btn btn-secondary mt-2">Cancel</button>
          </div>
        </div>

        <!-- Error Message -->
        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>

        <!-- Signup Link -->
        <div class="auth-footer">
          <p>New user? <router-link to="/signup" class="signup-link">Create an account</router-link></p>
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
      email: '',
      password: '',
      selectedRole: '',
      location: '',
      twoFACode: '',
      show2FA: false,
      errorMessage: '',
      showResetPassword: false,
      newPassword: '',
      forgotEmail: '',
      showForgotPassword: false,
      twoFACodeForReset: '',
      oldPassword: '',
      pwdChanged: false,
    };
  },
  methods: {
    async authenticate() {
      this.errorMessage = "";

      if (!this.show2FA) {
        if (!this.email || !this.password || !this.selectedRole || !this.location) {
          this.errorMessage = "Please fill in all fields!";
          return;
        }

        try {
          const response = await axios.post(`${API_URL}/login`, {
            email: this.email.trim(),
            password: this.password,
            role: this.selectedRole,
            location: this.location,
          });
          console.log("Initial Login Response:", response.data);
          if (response.data.message === "2FA Code required!") {
            this.show2FA = true;
            return;
          } else if (
            response.data.message ===
            "You are using the default password. Please reset your password before logging in."
          ) {
            this.errorMessage = response.data.message;
            this.showResetPassword = true;
            return;
          } else if (response.data.access_token) {
            this.pwdChanged = response.data.pwdChanged;
            localStorage.setItem("token", response.data.access_token);  // Use access_token
            localStorage.setItem("refreshToken", response.data.refresh_token);
            localStorage.setItem("isAuthenticated", "true");
            localStorage.setItem("userRole", response.data.role);
            this.$emit("login-success");
            this.$router.push('/').catch(err => console.error("Router error:", err));
          } else {
            this.errorMessage = "Unexpected response from server!";
          }
        } catch (error) {
          console.error("Initial Login Error:", error.response?.data);
          if (
            error.response?.status === 400 &&
            error.response?.data?.message === "2FA Code required!"
          ) {
            this.show2FA = true;
            return;
          }
          this.errorMessage = error.response?.data?.message || "Login failed!";
          return;
        }
      } else {
        if (!this.twoFACode) {
          this.errorMessage = "Please enter the 2FA code!";
          return;
        }

        try {
          const response = await axios.post(`${API_URL}/login`, {
            email: this.email.trim(),
            password: this.password,
            role: this.selectedRole,
            location: this.location,
            otp_code: this.twoFACode,
          });
          console.log("2FA Response:", response.data);
          if (response.data.access_token) {
            localStorage.setItem("token", response.data.access_token);  // Use access_token
            localStorage.setItem("refreshToken", response.data.refresh_token);
            localStorage.setItem("isAuthenticated", "true");
            localStorage.setItem("userRole", response.data.role);
            this.$emit("login-success");
            this.$router.push('/').catch(err => console.error("Router error:", err));
          } else {
            this.errorMessage = "Login failed: No token received!";
          }
        } catch (error) {
          console.error("2FA Error:", error.response?.data);
          this.errorMessage = error.response?.data?.message || "Invalid 2FA Code!";
        }
      }
    },
    // Keep resetPassword and forgotPassword unchanged
  },
};
</script> 

<style scoped>
/* 🌟 Page Wrapper */
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

/* 🛠️ Auth Content - FLEX CONTAINER */
.auth-content {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  gap: 30px;
  padding: 20px;
  flex-wrap: wrap; /* Ensures responsiveness */
}

/* 📌 Common Card Style */
.auth-box,
.image-container {
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

/* 🖼️ Image Container */
.image-container {
  align-items: center;
  order: -1; /* Ensures image is on the left */
}

/* 📷 Images */
.info-image {
  width: 100%;
  height: auto;
  max-height: 200px;
  border-radius: 8px;
  margin-bottom: 10px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

/* 📝 Title & Instructions */
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

/* 🖊️ Form Elements */
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

/* 🔘 Buttons */
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

/* 🎯 Button Container (Fixes Overlap) */
.button-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

/* ⚠️ Error Message */
.error-text {
  color: red;
  font-size: 0.9rem;
  margin-top: 10px;
}

/* 📌 Footer */
.auth-footer {
  margin-top: 10px;
  font-size: 0.9rem;
}

/* 📱 Responsive Design */
@media (max-width: 900px) {
  .auth-content {
    flex-direction: column; /* Stacks on small screens */
    gap: 20px;
  }

  .auth-box,
  .image-container {
    width: 90%;
    max-width: 400px;
  }
}
</style>
