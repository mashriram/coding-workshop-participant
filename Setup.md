# 🚀 ACME Performance Platform Deployment Guide

This guide provides instructions for deploying the ACME Performance Platform in a production-ready environment using Docker and Docker Compose.

## 📋 Prerequisites

Before you begin, ensure the target machine (e.g., AWS EC2 Ubuntu 22.04) has the following installed:

1.  **Docker**: [Install Docker](https://docs.docker.com/engine/install/ubuntu/)
2.  **Docker Compose**: [Install Docker Compose v2](https://docs.docker.com/compose/install/linux/)
3.  **Git**: `sudo apt update && sudo apt install git -y`

---

## 🏗️ One-Shot Deployment

We have provided a one-shot deployment script that handles the entire setup, including database initialization and seeding.

1.  **Clone the Repository**:
    ```bash
    git clone <your-repo-url>
    cd coding-workshop-participant
    ```

2.  **Run the Production Script**:
    ```bash
    chmod +x run-production.sh
    ./run-production.sh
    ```

The script will:
- Stop and clean any existing containers.
- Build the optimized Backend and Frontend images.
- Start the PostgreSQL 16 database.
- Initialize all database schemas (Auth, Employees, Goals, etc.).
- Seed sample data for all three portals.

---

## 🔑 Access Credentials

Once deployed, you can access the platform at `http://<your-ec2-ip>:3000`.

| Portal | Email | Password | Access Level |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin@acme.com` | `Admin@1234` | Full access to all systems and users. |
| **HR** | `hr@acme.com` | `HR@1234` | Employee management, training, and analytics. |
| **Manager** | `manager@acme.com` | `Manager@1234` | Team performance, goals, and reviews. |
| **Employee** | `employee@acme.com` | `Employee@1234` | Personal profile, goals, and training. |

---

## 🛠️ Operational Commands

### View Logs
To monitor the platform or troubleshoot:
```bash
docker compose logs -f
```

### Reset System
To wipe all data and start fresh:
```bash
docker compose down -v
./run-production.sh
```

### Backend API Documentation
The API follows a unified structure. Swagger/OpenAPI documentation (if enabled) is available at:
`http://<your-ec2-ip>:8000/docs`

---

## 🔒 Security Recommendations

For a true production deployment on EC2, please consider:
1.  **Restricting Ports**: Use an AWS Security Group to only allow port `3000` (Frontend) and `22` (SSH). Port `8000` should be kept internal if used behind Nginx.
2.  **Environment Variables**: Update `JWT_SECRET` in `docker-compose.yml` to a strong, random string.
3.  **SSL/TLS**: Use a reverse proxy like Caddy or Nginx with Let's Encrypt to enable HTTPS.
4.  **Database Backups**: Set up automated volumes backups for the `postgres_data` volume.
