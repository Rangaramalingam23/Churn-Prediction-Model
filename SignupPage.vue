<template>
    <div class="auth-container">
      <div class="auth-content">
        
        <!-- Left Side: Google Authenticator Info -->
        <div class="info-card">
          <h2>Two-Factor Authentication (2FA)</h2>
          <p class="auth-info">
            To enhance security, we require <strong>Google Authenticator</strong> for <strong>TOTP</strong>-based 2FA.
            <br /><br />
            <strong>Step 1:</strong> Install <strong>Google Authenticator</strong> on your mobile device.
            <br />
            <strong>Step 2:</strong> Scan the QR code after signing up.
          </p>
  
          <!-- 2FA Image -->
          <img :src="require('@/assets/2fa_security.png')" alt="2 Factor Authentication" class="info-image" />
        </div>
  
        <!-- Right Side: Signup Form -->
        <div class="auth-box">
          <h2>Signup</h2>
          <p class="auth-instruction">
            Before signing up, please install <strong>Google Authenticator</strong> on your mobile device.
            You will need it to set up <strong>TOTP</strong>-based 2FA during signup.
          </p>
          
          <form @submit.prevent="signup">
            <div class="form-group">
              <label>Email</label>
              <input type="text" v-model="email" required class="form-control" />
            </div>
            <div class="form-group">
              <label>Location</label>
              <input type="text" v-model="location" required class="form-control" placeholder="Enter your location" />
            </div>
            <div class="form-group">
              <label>Password</label>
              <input type="password" v-model="password" required class="form-control" />
            </div>
            <div class="form-group">
              <label>Role</label>
              <select v-model="selectedRole" required class="form-control">
                <option value="">Choose Role</option>
                <option value="user">User</option>
                <option v-if="!adminExists" value="admin">Admin</option>
              </select>
            </div>
            <button type="submit" class="btn btn-primary">Signup</button>
  
            <!-- Error Message -->
            <p v-if="errorMessage" class="text-danger">{{ errorMessage }}</p>
  
            <!-- QR Code Section (Inside the Form) -->
            <div v-if="qrCode" class="qr-container">
              <h3>Scan this QR Code in <strong>Google Authenticator</strong></h3>
              <img :src="'data:image/png;base64,' + qrCode" alt="Google Authenticator QR" class="qr-image" />
            </div>
          </form>
  
          <div class="auth-footer">
            <p>Already have an account? <router-link to="/login">Login</router-link></p>
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
        qrCode: '',
        errorMessage: '',
        location: '',
        adminExists: false
      };
    },
    async created() {
      await this.checkAdminRole();
    },
    methods: {
      async checkAdminRole() {
        try {
          const response = await axios.get(`${API_URL}/check-admin-role`);
          this.adminExists = response.data.adminExists;
        } catch (error) {
          this.errorMessage = "Failed to check admin role!";
        }
      },
      async signup() {
        this.errorMessage = "";
        this.qrCode = "";
  
        try {
          const response = await axios.post(`${API_URL}/register`, {
            email: this.email,
            password: this.password,
            role: this.selectedRole,
            location: this.location
          });
  
          if (response.data.qr_code) {
            this.qrCode = response.data.qr_code;
          }
        } catch (error) {
          this.errorMessage = error.response?.data?.message || "Signup failed!";
        }
      }
    }
  };
  </script>
  
  <style scoped>
  /* Container */
  .auth-container {
    display: flex;
    flex-direction: column;
    min-height: 100vh;
    background-color: #f4f4f4;
  }
  
  /* Ensure content grows */
  .auth-content {
    flex-grow: 1;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 40px;
    padding: 20px;
  }
  
  /* Left Side: Info Card */
  .info-card {
    width: 400px;
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    text-align: center;
  }
  
  .info-card h2 {
    margin-bottom: 10px;
  }
  
  .auth-info {
    font-size: 16px;
    color: #444;
    background: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    border-left: 4px solid #007bff;
    text-align: left;
    line-height: 1.5;
    font-weight: 500;
  }
  
  .info-image {
    width: 100%;
    margin-top: 15px;
    border-radius: 8px;
  }
  
  /* Right Side: Signup Form */
  .auth-box {
    width: 400px;
    padding: 20px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    text-align: center;
  }
  
  .auth-box h2 {
    margin-bottom: 10px;
  }
  
  .auth-instruction {
    font-size: 14px;
    color: #666;
    margin-bottom: 15px;
  }
  
  /* Form */
  .form-group {
    text-align: left;
    margin-bottom: 12px;
  }
  
  .form-group label {
    display: block;
    font-size: 14px;
    font-weight: bold;
    margin-bottom: 5px;
  }
  
  .form-control {
    width: 100%;
    padding: 12px;
    border: 1px solid #ccc;
    border-radius: 5px;
    font-size: 14px;
  }
  
  /* Signup Button */
  .btn-primary {
    width: 100%;
    padding: 12px;
    background: #007bff;
    color: white;
    border: none;
    cursor: pointer;
    border-radius: 5px;
    font-size: 14px;
  }
  
  .btn-primary:hover {
    background: #0056b3;
  }
  
  /* QR Code Container (Now Inside Form) */
  .qr-container {
    margin-top: 15px;
    padding: 10px;
    background: #f8f9fa;
    border-radius: 8px;
    text-align: center;
  }
  
  .qr-container h3 {
    font-size: 16px;
    margin-bottom: 10px;
  }
  
  .qr-image {
    width: 180px;
    height: 180px;
    border-radius: 8px;
  }
  
  /* Error Message */
  .text-danger {
    color: red;
    font-size: 14px;
    margin-top: 10px;
  }
  
  /* Footer */
  .auth-footer {
    margin-top: 10px;
    font-size: 14px;
  }
  
  .auth-footer a {
    color: #007bff;
    cursor: pointer;
    text-decoration: none;
  }
  
  .auth-footer a:hover {
    text-decoration: underline;
  }
  </style>