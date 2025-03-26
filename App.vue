<template>
  <div id="app" class="app-container">
    <header class="header" v-if="shouldShowHeader">
      <div class="header-content">
        <div class="icon-container">
          <img v-if="leftIcon" :src="iconSrc(leftIcon.icon)" alt="Left Icon" class="icon" />
        </div>
        <h1 class="title">{{ title }}</h1>
        <div class="icon-container right-icons">
          <img
            v-if="rightIcon"
            :src="iconSrc(rightIcon.icon)"
            alt="Right Icon"
            class="icon"
          />
          <!-- Logout button only visible on home page when authenticated -->
          <img 
            :src="require('@/assets/logout.png')" 
            alt="Logout" 
            class="icon logout-icon" 
            @click="logout"
            v-if="$route.path === '/' && isAuthenticated"
          />
          <!-- User Management only for admin -->
          <img 
            :src="require('@/assets/management.png')" 
            alt="User Management" 
            class="icon management-icon" 
            @click="navigateToUserManagement"
            v-if="isAdmin"
          />
        </div>
      </div>
      <div class="Header-Nav">
        <HorizontalAnnouncements class="announcements-bar"/>
        <AppNav class="app-nav" />
      </div>
    </header>
    <main class="content">
      <router-view @login-success="handleLoginSuccess" />
    </main>
    <footer class="footer">
      <div class="footer-logo">
        <img :src="logo1" alt="Logo 1" />
      </div>
      <div class="footer-logo">
        <img :src="logo2" alt="Logo 2" />
      </div>
      <div class="footer-logo">
        <img :src="logo3" alt="Logo 3" />
      </div>
    </footer>
  </div>
</template>

<script>
import AppNav from "@/views/AppNav.vue";
import HorizontalAnnouncements from "@/views/Announcements.vue";
import { fetchDefaultMetrics, fetchHeader, create_c_alert, create_w_alert } from "@/services/DataService.js";
import performanceMetrics from "../performance.json";

export default {
  name: "App",
  components: {
    AppNav,
    HorizontalAnnouncements,
  },
  data() {
    return {
      performanceMetrics,
      title: "GIAS-GePNIC Infrastructure Alert System",
      leftIcon: null,
      rightIcon: null,
      default_cls: null,
      default_fcp: null,
      default_lcp: null,
      default_speedIndex: null,
      default_tbt: null,
      logo1: require("@/assets/nic-logo.png"),
      logo2: require("@/assets/di-logo.png"),
      logo3: require("@/assets/nicse-logo.png"),
      portalcheckTimer: null,
      token: null,
      userRole: null,
      isDataLoaded: false,
    };
  },
  computed: {
    isAuthenticated() {
      const token = this.token || localStorage.getItem("token") || localStorage.getItem("authToken");
      console.log("Computed isAuthenticated - token:", token);
      return !!token;
    },
    isAdmin() {
      const role = this.userRole || localStorage.getItem("userRole");
      console.log("Computed isAdmin - userRole:", role);
      return this.isAuthenticated && role === "admin";
    },
    shouldShowHeader() {
      return this.isAuthenticated || this.isDataLoaded || !['/login', '/signup'].includes(this.$route.path);
    },
  },
  created() {
    this.updateAuthState();
    console.log("Created - token:", this.token, "userRole:", this.userRole);

    // Check if session is active; if not, clear localStorage (browser was closed)
    const isSessionActive = sessionStorage.getItem("activeSession");
    console.log("Created - isSessionActive:", isSessionActive);
    if (!isSessionActive && this.token) {
      console.log("No active session found, clearing localStorage...");
      localStorage.clear();
      this.token = null;
      this.userRole = null;
    }

    if (!this.isAuthenticated && !['/login', '/signup'].includes(this.$route.path)) {
      console.log("Not authenticated, redirecting to /login from created");
      this.$router.push("/login").catch(() => {});
    }
  },
  async mounted() {
    console.log("Mounted - token:", this.token, "userRole:", this.userRole);
    console.log("Current route:", this.$route.path);

    if (this.isAuthenticated) {
      await this.loadInitialData();
      // Set flag in sessionStorage to indicate active session
      sessionStorage.setItem("activeSession", "true");
    } else {
      this.isDataLoaded = true;
    }

    // Watch route changes to update auth state
    this.$watch(
      () => this.$route.path,
      (newPath) => {
        console.log("Route changed to:", newPath);
        this.updateAuthState();
      }
    );
  },
  beforeUnmount() {
    if (this.portalcheckTimer) {
      clearInterval(this.portalcheckTimer);
    }
  },
  methods: {
    updateAuthState() {
      // Explicitly update token and userRole from localStorage
      this.token = localStorage.getItem("token") || localStorage.getItem("authToken");
      this.userRole = localStorage.getItem("userRole");
      console.log("Updated auth state - token:", this.token, "userRole:", this.userRole);
    },
    handleLoginSuccess() {
      // Called from LoginPage when login succeeds
      this.updateAuthState();
      if (this.isAuthenticated) {
        this.loadInitialData();
        // Set flag in sessionStorage after successful login
        sessionStorage.setItem("activeSession", "true");
      }
    },
    async loadInitialData() {
      try {
        const metrics = await fetchDefaultMetrics();
        this.default_lcp = metrics[0][0];
        this.default_fcp = metrics[0][1];
        this.default_speedIndex = metrics[0][2];
        this.default_tbt = metrics[0][3];
        this.default_cls = metrics[0][4];

        const data = await fetchHeader();
        this.title = data.title;
        data.icons.forEach((icon) => {
          if (icon.position === "left") {
            this.leftIcon = icon;
          } else if (icon.position === "right") {
            this.rightIcon = icon;
          }
        });

        this.startPortalCheckTimer();
        console.log("Data loaded successfully:", this.title, this.leftIcon, this.rightIcon);
      } catch (error) {
        console.error("Error fetching initial data:", error);
        this.title = "Error Loading Title";
      } finally {
        this.isDataLoaded = true;
      }
    },
    iconSrc(base64Data) {
      return `data:image/png;base64,${base64Data}`;
    },
    portalcheck() {
      performanceMetrics.map(async (elem) => {
        if (elem["fcp"] === undefined) {
          create_c_alert(elem["url"], elem["instance"]);
        }
        const fcp = parseFloat(elem["fcp"].replace("\u00A0s", "")) || 0;
        const lcp = parseFloat(elem["lcp"].replace("\u00A0s", "")) || 0;
        const speedIndex = parseFloat(elem["speedIndex"].replace("\u00A0s", "")) || 0;
        const tbt = parseFloat(elem["tbt"].replace("\u00A0ms", "")) || 0;
        const cls = parseFloat(elem["cls"]) || 0;

        const allMetricsWithinThresholds =
          cls <= this.default_cls &&
          fcp <= this.default_fcp &&
          lcp <= this.default_lcp &&
          speedIndex <= this.default_speedIndex &&
          tbt <= this.default_tbt;

        if (!allMetricsWithinThresholds) {
          console.log("Creating an error ");
          await create_w_alert(elem["url"], elem["instance"]);
        }
      });
    },
    startPortalCheckTimer() {
      this.portalcheckTimer = setInterval(() => {
        this.portalcheck();
      }, 3600000);
    },
    logout() {
      console.log("Logging out...");
      localStorage.removeItem("token");
      localStorage.removeItem("authToken");
      localStorage.removeItem("userRole");
      localStorage.removeItem("refreshToken");
      localStorage.removeItem("isAuthenticated");
      localStorage.removeItem("theme");
      sessionStorage.removeItem("activeSession"); // Clear session flag on manual logout
      this.token = null;
      this.userRole = null;
      this.$router.push("/login").then(() => {
        console.log("Redirected to /login");
      }).catch((err) => {
        console.error("Logout redirect error:", err);
      });
    },
    navigateToUserManagement() {
      console.log("Navigating to /user-management");
      this.$router.push("/user-management").catch((err) => {
        console.error("Navigation error:", err);
      });
    },
  },
};
</script>

<style scoped>
.app-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.announcements-bar {
  position: absolute;
  display: flex;
  width: 81%;
  max-width: 4800px;
  right: 19%;
  top: 83px;
  margin-top: 8px;
  z-index: 1000;
  height: 3vw;
  justify-content: space-around;
}
.dark .announcements-bar {
  background-color: rgb(23 17 76);
}
.light .announcements-bar {
  background-color: rgb(255 255 255);
}
.header {
  display: flex;
  flex-direction: column;
  background-color: rgb(255, 255, 255);
  color: white;
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 1000;
}
.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: rgb(62, 131, 205);
}
.light .header-content {
  color: white;
  background-color: rgb(62, 131, 205);
}
.dark .header-content {
  background-color: rgb(35, 68, 139);
  color: #f5f5f5;
}
.icon-container {
  display: flex;
  align-items: center;
}
.right-icons {
  display: flex;
  gap: 15px; /* Space between the three icons */
  padding-right: 10px; /* Optional: adds some padding on the right */
}
.icon {
  height: 50px; /* Consistent size for all icons */
}
.logout-icon, .management-icon {
  height: 50px; /* Match the size of the rightIcon */
  cursor: pointer;
}
.logout-icon:hover, .management-icon:hover {
  opacity: 0.8;
}
.title {
  text-align: center;
  flex: 1;
}
.app-nav {
  width: 20.2%;
  left: 82%;
}
.content {
  flex: 1;
  padding: 20px;
  padding-top: 150px;
  width: 98vw;
  left: -0.5vw;
  position: relative;
}
.dark .content {
  background-color: #262626;
}
.light .content {
  background-color: JESUS;
}
.footer {
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 10px;
  background-color: rgb(255, 255, 255);
  color: white;
  position: fixed;
  bottom: 0;
  left: 0;
  width: 100%;
  z-index: 1000;
}
.footer-logo img {
  height: 30px;
}
</style>