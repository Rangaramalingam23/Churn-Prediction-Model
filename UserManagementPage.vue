<template>
    <div>
      <div class="container">
        <h2>User Management</h2>
  
        <!-- Pending Users Table -->
        <h3>Pending Users</h3>
        <table v-if="pendingUsers.length > 0" class="user-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Location</th>
              <th>IP Address</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in pendingUsers" :key="user.email">
              <td>{{ user.email }}</td>
              <td>{{ user.location }}</td>
              <td>{{ user.ip_address }}</td>
              <td>
                <button class="approve-btn" @click="approveUser(user.email)">Approve</button>
                <button class="ignore-btn" @click="openRejectPopup(user)">Reject</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else>No pending users found.</p>
  
        <!-- All Users Table -->
        <h3>All Users</h3>
        <table v-if="allUsers.length > 0" class="user-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th>Location</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in allUsers" :key="user.email">
              <td>{{ user.email }}</td>
              <td>{{ user.role }}</td>
              <td>{{ user.status }}</td>
              <td>{{ user.location }}</td>
              <td>
                <button class="disable-btn" @click="disableUser(user.email)">Disable</button>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-else>No users found.</p>
  
        <!-- Reject Reason Popup -->
        <div v-if="showRejectPopup" class="popup-overlay">
          <div class="popup-box">
            <h3>Reject User</h3>
            <p>Enter the reason for rejecting <b>{{ selectedUser.email }}</b>:</p>
            <input
              type="text"
              v-model="rejectReason"
              placeholder="Enter reject reason"
              class="popup-input"
            />
            <div class="popup-buttons">
              <button class="popup-submit-btn" @click="submitRejectReason">Submit</button>
              <button class="popup-cancel-btn" @click="closeRejectPopup">Cancel</button>
            </div>
          </div>
        </div>
  
        <!-- Error Message -->
        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
      </div>
    </div>
  </template>
  
  <script>
  import axios from "axios";
  import API_URL from "@/services/config.js";

  export default {
    data() {
      return {
        pendingUsers: [],
        allUsers: [],
        errorMessage: "",
        showRejectPopup: false,
        selectedUser: null,
        rejectReason: ""
      };
    },
    methods: {
      async fetchPendingUsers() {
        try {
          const token = localStorage.getItem("authToken");
          const response = await axios.get(`${API_URL}/user-management`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          // Add showRejectReason and rejectReason fields to each user
          this.pendingUsers = response.data.pending_users.map(user => ({
            ...user,
            showRejectReason: false,
            rejectReason: ""
          }));
        } catch (error) {
          this.errorMessage = error.response?.data?.message || "Failed to fetch users!";
        }
      },
      async fetchAllUsers() {
        try {
          const token = localStorage.getItem("authToken");
          const response = await axios.get(`${API_URL}/all-users`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          this.allUsers = response.data.all_users;
        } catch (error) {
          this.errorMessage = error.response?.data?.message || "Failed to fetch users!";
        }
      },
      async approveUser(email) {
        try {
          const token = localStorage.getItem("authToken");
          await axios.post(
            `${API_URL}/approve-user`,
            { email },
            { headers: { Authorization: `Bearer ${token}` }}
          );
          this.fetchPendingUsers(); // Refresh the list
        } catch (error) {
          this.errorMessage = error.response?.data?.message || "Failed to approve user!";
        }
      },
      async submitRejectReason() {
      if (!this.rejectReason) {
        this.errorMessage = "Reject reason is required!";
        return;
      }
      try {
        const token = localStorage.getItem("authToken");
        await axios.post(
          `${API_URL}/reject-user`,
          { email: this.selectedUser.email, rejectreason: this.rejectReason },
          { headers: { Authorization: `Bearer ${token}` } }
        );
        this.showRejectPopup = false;
        this.fetchPendingUsers();
      } catch (error) {
        this.errorMessage = error.response?.data?.message || "Failed to reject user!";
      }
    },
      openRejectPopup(user) {
      this.selectedUser = user;
      this.rejectReason = "";
      this.showRejectPopup = true;
    },
    closeRejectPopup() {
      this.showRejectPopup = false;
    },
      async disableUser(email) {
        try {
          const token = localStorage.getItem("authToken");
          await axios.post(
            `${API_URL}/disable-user`,
            { email },
            { headers: { Authorization: `Bearer ${token}` }}
          );
          this.fetchAllUsers(); // Refresh the list
        } catch (error) {
          this.errorMessage = error.response?.data?.message || "Failed to disable user!";
        }
      }
    },
    mounted() {
      this.fetchPendingUsers();
      this.fetchAllUsers();
    }
  };
  </script>
  
  <style scoped>
  /* Container */
  .container {
    max-width: 900px;
    margin: auto;
    text-align: center;
    background-color: #f9f9f9;
    padding: 20px;
    border-radius: 10px;
    box-shadow: 0px 0px 10px rgba(0, 0, 0, 0.1);
  }
  
  /* Headers */
  h2, h3 {
    color: #333;
    margin-bottom: 10px;
  }
  
  /* Table */
  .user-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 20px;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.1);
  }
  
  /* Table Headers */
  .user-table th {
    background: #007bff;
    color: white;
    padding: 12px;
    text-align: left;
  }
  
  /* Table Cells */
  .user-table td {
    border: 1px solid #ddd;
    padding: 12px;
    text-align: left;
  }
  
  /* Alternate Row Colors */
  .user-table tr:nth-child(odd) {
    background: #ffffff;
  }
  
  .user-table tr:nth-child(even) {
    background: #f8f9fa; /* Light gray to fix visibility issue */
  }
  
  /* Hover Effect */
  .user-table tr:hover {
    background: #e0f7fa;
    transition: 0.3s;
  }
  
  /* Buttons */
  button {
    border: none;
    padding: 8px 12px;
    border-radius: 5px;
    font-size: 14px;
    cursor: pointer;
    margin-right: 5px;
    transition: 0.3s ease-in-out;
  }
  
  /* Approve Button */
  .approve-btn {
    background-color: #28a745;
    color: white;
  }
  
  .approve-btn:hover {
    background-color: #218838;
  }
  
  /* Reject Button */
  .ignore-btn {
    background-color: #dc3545;
    color: white;
  }
  
  .ignore-btn:hover {
    background-color: #c82333;
  }
  
  /* Disable Button */
  .disable-btn {
    background-color: #6c757d;
    color: white;
  }
  
  .disable-btn:hover {
    background-color: #5a6268;
  }
  
  /* Popup Overlay */
  .popup-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
  }
  
  /* Popup Box */
  .popup-box {
    background: white;
    padding: 20px;
    border-radius: 8px;
    width: 300px;
    text-align: center;
    box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.2);
  }
  
  /* Popup Input */
  .popup-input {
    width: 90%;
    padding: 8px;
    margin-top: 10px;
    border: 1px solid #ccc;
    border-radius: 5px;
  }
  
  /* Popup Buttons */
  .popup-buttons {
    margin-top: 15px;
  }
  
  /* Submit Button */
  .popup-submit-btn {
    background-color: #ff4d4d;
    color: white;
    padding: 8px 12px;
    border-radius: 5px;
    cursor: pointer;
    margin-right: 5px;
  }
  
  .popup-submit-btn:hover {
    background-color: #ff1a1a;
  }
  
  /* Cancel Button */
  .popup-cancel-btn {
    background-color: #6c757d;
    color: white;
    padding: 8px 12px;
    border-radius: 5px;
    cursor: pointer;
  }
  
  .popup-cancel-btn:hover {
    background-color: #5a6268;
  }
  
  /* Error Message */
  .error-text {
    color: red;
    margin-top: 10px;
    font-weight: bold;
  }
  </style>