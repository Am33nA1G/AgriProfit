1️⃣ Product Definition

AgriProfit is a cloud-based SaaS platform that helps farmers across India make better decisions using historical commodity price analytics, basic price forecasting insights, transport cost comparison, and community-driven discussions with district-level alerting, delivered via web and mobile applications.

2️⃣ Target Users
Primary User

Farmer

Geography

Pan-India (All districts of Kerala for v1, expandable to other states)

Language Support (v1)

English

Malayalam

3️⃣ Core Modules (Frozen Scope)

These are the only modules to be built in this project.

1. Authentication & User Management

Phone number + OTP login

Role-based access (Farmer, Admin)

User profile with district selection (manual during registration)

Account deletion capability with 30-day grace period

2. Commodity Price Analytics

Historical price visualization

Trends and comparisons

Simple, explainable analytics usable by farmers

Commodities covered: Rice, Wheat, Coconut, Rubber, Pepper, Cardamom, Banana, Tapioca, Vegetables (Tomato, Onion, Potato)

Data updated: Daily (scraped from government sources or manually entered by admins)

3. Price Prediction / Forecasting (Lightweight)

Basic forecasting based on historical data

Time horizons: 7-day and 30-day forecasts

Field-usable accuracy: Minimum 70% directional accuracy (up/down/stable)

Fallback: If model fails, display "Insufficient data for forecast"

No overhyped ML claims

4. Transport Cost Comparison

Simple cost calculation: cost = distance × rate

Distance: Straight-line distance between district centers (no maps API required)

Rate: Admin-configurable per-km rate (default: ₹8/km)

User inputs: Origin district, destination district, commodity weight

No route optimization

No provider marketplace

5. Community Discussions

Farmers can create posts (text-based, max 500 characters)

Posts visible to all users

Standard discussion threads

Farmers can edit their own posts within 1 hour of posting

Farmers can delete their own posts anytime

Spam prevention: Max 10 posts per user per day

6. Alert System (Special Post Type)

Alerts appear as red-highlighted posts for all users

Alerts are:

Pinned & prominently highlighted for:

Same district users

Neighboring district users (districts sharing a border)

Admins can broadcast system-wide alerts

Alerts remain pinned for 48 hours or until manually unpinned by admin

7. In-App Notifications

Notification feed inside the app

Triggered by:

Alerts (district-relevant)

Admin announcements

New replies to user's posts

Notifications retained for 30 days

8. Admin Dashboard

User monitoring (total users, active users, registrations per day)

Alert moderation (create, edit, delete, pin/unpin)

System-level announcements

Community content moderation (hide/delete inappropriate posts)

Commodity price data management (manual entry/update)

Transport rate configuration

Basic analytics visibility (user activity, popular commodities, post engagement)

4️⃣ User Roles & Permissions
Farmer

Register and log in via phone + OTP

Select district during registration (dropdown list)

View historical prices and analytics

View price forecasts

Compare transport costs

Create community posts (max 10/day)

Edit own posts (within 1 hour)

Delete own posts (anytime)

Create alert posts (visible to same + neighboring districts)

Receive in-app notifications

Request account deletion

Admin

All farmer permissions

Broadcast alerts (system-wide or district-specific)

Pin/override alerts

Moderate community content (hide/delete any post)

Monitor system usage

Manage commodity price data

Configure transport rates

Manage user accounts (view, suspend, delete)

⚠ No additional roles will be added.

5️⃣ Platforms & Technology Stack (Locked)

Web App: Next.js (React)

Mobile App: React Native

Backend API: FastAPI (Python)

Database: PostgreSQL

Caching: Redis (for session management and frequently accessed data)

Deployment: Docker + Docker Compose

Cloud Provider: AWS (using free-tier eligible services: EC2, RDS, S3)

Alternative: DigitalOcean (if AWS free-tier limits are exceeded)

Single backend shared by web and mobile.

6️⃣ Data Sources & Integration

Commodity Price Data Sources

Primary: Agmarknet (Government of India portal)

Secondary: Manual entry by admins

Tertiary: Kerala State Civil Supplies Corporation (when available)

Data Collection Method

Daily scraping script (automated where possible)

Admin dashboard for manual entry/correction

Historical data: Minimum 12 months for each commodity

District Data

Complete list of Kerala districts (14 districts)

District boundaries (neighboring district mapping): Predefined configuration file

User district selection: Dropdown during registration (cannot be changed later without admin approval)

7️⃣ Non-Negotiable Requirements

These must be satisfied.

Single backend for web & mobile

API-first architecture

Secure phone + OTP authentication (using Twilio or similar service)

Role-based access control (RBAC)

Cloud deployable using Docker

Production-grade error handling

Logging and audit trails (all user actions logged)

Designed to support 1000+ concurrent users (theoretical)

Response time SLA: < 2 seconds for 95% of API requests under normal load

Data encryption: SSL/TLS in transit, encrypted database storage

API rate limiting: 100 requests per minute per user

Suitable for KTU academic evaluation

Low-cost / free-tier cloud compatible (target monthly cost: < ₹2000)

If something violates these, it is rejected.

8️⃣ Security & Privacy

Authentication & Authorization

Phone + OTP (6-digit code, 5-minute expiry)

JWT tokens for session management (7-day expiry)

Role-based access control enforced at API level

Data Protection

HTTPS/TLS for all API communications

PostgreSQL encryption at rest

Passwords/sensitive data hashed using bcrypt

SQL injection protection (parameterized queries)

XSS protection (input sanitization)

CSRF protection (token-based)

Privacy & Compliance

User data retained: Indefinitely (unless user requests deletion)

Account deletion: 30-day grace period, then permanent deletion

No personal data sharing with third parties

Privacy policy displayed during registration

Users can export their data (JSON format)

Audit & Logging

All user actions logged (login, post creation, alerts, etc.)

Admin actions logged separately (moderation, data changes)

Logs retained for 90 days

Failed login attempts monitored (5 failed attempts = 15-minute lockout)

9️⃣ Out of Scope (Explicitly Not Built)

The following will not be implemented:

Payments or subscriptions

SMS or email notifications (only in-app notifications)

Offline-first mobile mode

Advanced ML or deep learning models

Real-time bidding or auctions

Government scheme automation

Chatbots or conversational AI

Blockchain or Web3 features

Maps API integration (using straight-line distance instead)

Multi-language support beyond English and Malayalam

Image/video uploads in posts

Real-time chat or messaging

Push notifications (only in-app notification feed)

No exceptions.

🔟 Testing Requirements

Unit Testing

Minimum 70% code coverage for backend (FastAPI)

Minimum 60% code coverage for frontend (Next.js, React Native)

Testing framework: pytest (backend), Jest (frontend)

Integration Testing

API endpoint testing (all CRUD operations)

Authentication flow testing

Role-based access testing

End-to-End Testing

Critical user journeys tested:

Farmer registration and login

Price analytics viewing

Transport cost calculation

Post creation and alert system

Admin moderation workflow

Performance Testing

Load testing: 1000 concurrent users (using Locust or Apache JMiner)

Response time validation: 95% requests < 2 seconds

Database query optimization validated

Security Testing

OWASP Top 10 vulnerability checks

Penetration testing (basic level)

Authentication/authorization bypass testing

1️⃣1️⃣ Success Criteria (Definition of "Done")

This project is considered complete when:

✅ Web application is fully functional across all modules

✅ Mobile application is fully functional across all modules

✅ Backend API is deployed on AWS/DigitalOcean

✅ Docker-based deployment works end-to-end

✅ PostgreSQL database is configured and populated with sample data

✅ All core modules are usable by real farmers

✅ Alerts behave correctly by district logic (same + neighboring)

✅ Admin controls function as specified

✅ APIs are documented (Swagger/OpenAPI)

✅ Test coverage meets minimum thresholds (70% backend, 60% frontend)

✅ Performance benchmarks met (1000 concurrent users, <2s response time)

✅ System is demo-ready and evaluable

✅ User documentation created (Farmer guide, Admin manual)

✅ Technical documentation complete (Architecture, API docs, Deployment guide)

✅ KTU project report submitted (as per academic requirements)

1️⃣2️⃣ Project Timeline & Milestones

Total Duration: 16 weeks

Phase 1: Planning & Setup (Weeks 1-2)

Finalize tech stack and architecture

Set up development environment

Create database schema

Set up CI/CD pipeline

Initialize project repositories

Phase 2: Backend Development (Weeks 3-6)

Authentication & user management

Commodity price analytics APIs

Price forecasting module

Transport cost calculation

Community discussions APIs

Alert system APIs

Admin dashboard APIs

Phase 3: Frontend Development (Weeks 7-10)

Web application (Next.js)

Mobile application (React Native)

UI/UX implementation

Integration with backend APIs

Phase 4: Testing & QA (Weeks 11-12)

Unit testing

Integration testing

End-to-end testing

Performance testing

Security testing

Bug fixes

Phase 5: Deployment & Documentation (Weeks 13-14)

Cloud deployment (AWS/DigitalOcean)

Production environment setup

API documentation (Swagger)

User documentation (guides and manuals)

Technical documentation

Phase 6: Final Review & Submission (Weeks 15-16)

End-to-end system testing

Demo preparation

KTU project report completion

Final presentation preparation

Submission to KTU

Key Milestones:

Week 2: Development environment ready ✓

Week 6: Backend APIs complete ✓

Week 10: Frontend applications complete ✓

Week 12: Testing complete ✓

Week 14: Deployment complete ✓

Week 16: Project submission ✓

1️⃣3️⃣ Team & Responsibilities

This section should be filled based on your actual team:

Team Size: [To be filled]

Roles:

Backend Developer(s): [Names]

Frontend Developer(s) - Web: [Names]

Frontend Developer(s) - Mobile: [Names]

UI/UX Designer: [Names]

QA/Testing: [Names]

Project Manager: [Names]

DevOps: [Names]

Decision-Making Authority:

Technical decisions: Team consensus with PM final say

Scope changes: Not allowed (scope is locked)

Bug fixes: Developer discretion for minor, PM approval for major

Deployment: DevOps lead with PM approval

1️⃣4️⃣ Deployment Specifications

Environments

Development: Local Docker containers

Staging: Cloud-based (AWS EC2 t2.micro or DigitalOcean Basic Droplet)

Production: Cloud-based (AWS EC2 t2.small or DigitalOcean Standard Droplet)

Cloud Infrastructure (AWS Option)

Compute: EC2 t2.small (2 vCPU, 2GB RAM)

Database: RDS PostgreSQL (db.t3.micro, 20GB storage)

Cache: ElastiCache Redis (cache.t3.micro)

Storage: S3 (for logs and backups)

Load Balancer: Application Load Balancer (if traffic justifies)

Estimated monthly cost: ₹1500-2000

Cloud Infrastructure (DigitalOcean Alternative)

Droplet: Standard (2 vCPU, 4GB RAM, 80GB SSD) - $24/month (~₹2000)

Managed PostgreSQL: Basic (1GB RAM, 10GB storage) - $15/month (~₹1250)

Redis: Self-hosted on same droplet

Backups: Weekly automated snapshots

Estimated monthly cost: ₹3000-3500

CI/CD Pipeline

Version Control: GitHub

CI/CD: GitHub Actions

Automated workflows:

Run tests on pull requests

Build Docker images on merge to main

Deploy to staging automatically

Deploy to production on manual approval

Monitoring & Observability

Logging: Centralized logging (using Winston/Loguru)

Monitoring: Basic server monitoring (CPU, memory, disk usage)

Error tracking: Sentry (free tier)

Uptime monitoring: UptimeRobot (free tier)

1️⃣5️⃣ Accessibility & Usability

Web Application

Responsive design (mobile, tablet, desktop)

Minimum browser support: Chrome 90+, Firefox 88+, Safari 14+, Edge 90+

WCAG 2.1 Level A compliance (basic accessibility)

Keyboard navigation support

Mobile Application

Minimum Android version: 10.0 (API level 29)

Minimum iOS version: 13.0

Touch-friendly UI (minimum touch target: 44x44 pixels)

Offline graceful degradation (show cached data with staleness indicator)

User Experience

Maximum 3 clicks to reach any feature

Clear error messages with actionable guidance

Loading indicators for all async operations

Form validation with inline error messages

Help text and tooltips for complex features

1️⃣6️⃣ Documentation Deliverables

Technical Documentation

System architecture diagram

Database schema (ERD)

API documentation (Swagger/OpenAPI)

Deployment guide (step-by-step)

Environment setup guide

Codebase structure and conventions

Testing strategy and coverage report

User Documentation

Farmer user guide (with screenshots)

Admin manual (with workflows)

FAQ section

Troubleshooting guide

Academic Documentation

KTU project report (as per university format)

Project presentation slides

Demo video (5-10 minutes)

Code repository with README

1️⃣7️⃣ Assumptions & Constraints

Assumptions

Users have basic smartphone literacy

Users have stable internet connectivity (3G minimum)

Government data sources remain accessible

Phone numbers are unique per user

District boundaries do not change during project duration

Constraints

Budget: Maximum ₹5000 for entire project duration

Team availability: Part-time (academic project)

Timeline: Fixed 16-week deadline

Cloud resources: Limited to free/low-cost tiers

No external funding or monetization in v1

1️⃣8️⃣ Risk Management

Technical Risks

Risk: Government data sources become unavailable

Mitigation: Manual data entry fallback through admin dashboard

Risk: OTP service provider costs exceed budget

Mitigation: Use free-tier services (Twilio trial, Firebase Auth)

Risk: Performance issues with 1000 concurrent users

Mitigation: Load testing early, optimize database queries, implement caching

Risk: Mobile app compatibility issues

Mitigation: Test on multiple devices, use React Native stable version

Operational Risks

Risk: Team member unavailability

Mitigation: Cross-training, modular architecture, clear documentation

Risk: Scope creep despite locked scope

Mitigation: Strict adherence to this contract, regular scope reviews

Risk: Cloud costs exceeding budget

Mitigation: Monitor usage daily, set billing alerts, use cost-optimized instances

Academic Risks

Risk: Project not meeting KTU evaluation criteria

Mitigation: Regular check-ins with faculty, align with rubric, mock presentations

Risk: Delayed submission

Mitigation: Weekly progress tracking, buffer time in timeline, prioritize MVP

1️⃣9️⃣ Project Nature

Project Type: Mini Project (KTU Academic)

Quality Bar: Startup-grade, not demo-level

Name: AgriProfit (temporary, can rebrand later)

Team Collaboration: Git-based workflow with pull requests and code reviews

Communication: Weekly team meetings, daily async updates (Slack/Discord)

🔒 STATUS: LOCKED

From this point:

❌ No new features

❌ No scope expansion

❌ No platform changes

✅ Only execution, testing, and deployment

This contract is the single source of truth for the AgriProfit project.

Any deviations must be documented and justified in writing.

Last Updated: January 19, 2026
Version: 2.0 (Complete)