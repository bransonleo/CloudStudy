# Project Proposal II – Cloud Computing

# CloudStudy: AI-Powered Study Assistant

**Course:** CSD3156 Mobile and Cloud Computing  
**Team Number:** 10

## Team Members

| Name | Student ID |
|---|---|
| Leo Yew Siang, Branson | 2301321 |
| Chiu Jun Jie | 2301524 |
| Chua Sheng Kai Jovan | 2301244 |
| Cheong Jia Zen | 2301549 |

---

## 1. Introduction

Students regularly face the challenge of processing large volumes of study materials efficiently. Creating revision aids such as summaries, flashcards, and practice quizzes manually is time-consuming, and multilingual learners face the additional barrier of working across languages. While existing tools like Quizlet and Google's NotebookLM offer some of these features, they are not designed to demonstrate or leverage a full cloud-native, horizontally scalable architecture.

We propose CloudStudy, an AI-powered study assistant built as a cloud-based web application on AWS. The system allows users to upload study materials (PDFs, images or text) and automatically generates summaries, quiz questions, flashcards and translations using cloud-integrated AI services. The system follows an N-tier architecture that separates the frontend presentation, backend application logic, and data storage into distinct layers. An Application Load Balancer distributes incoming traffic across backend instances within an Auto-Scaling Group, while cloud object storage and a managed database handle file persistence and structured data respectively.

The application is designed around five key architectural goals as specified in the project requirements:

- **Functionality** as the primary focus, ensuring a complete and usable end-to-end workflow
- **Scalability** through horizontal scaling of backend servers behind a load balancer
- **Reliability** via health checks, automated instance recovery, and multi-availability-zone deployment
- **Elasticity** through auto-scaling policies that dynamically adjust compute capacity based on traffic demand
- **Security** through managed authentication, HTTPS termination at the load balancer, IAM least-privilege policies, and encryption at rest for both object storage and the database

Key technical challenges include handling diverse input formats (handwritten notes via OCR, typed PDFs, and raw text), orchestrating a multi-step AI processing pipeline with acceptable latency, and ensuring the system scales cost-efficiently under fluctuating student workloads such as peak exam periods.

The scope of work covers frontend development, backend API implementation, AI integration for content generation, cloud infrastructure provisioning, and testing.

---

## 2. Proposed Design and Components

Our system utilises a single baseline N-tier architecture deployed on the cloud, designed to separate the frontend presentation, backend processing, and data storage layers. To handle fluctuating student workloads, the compute layer incorporates horizontal scaling with auto-scaling mechanisms.

**System Workflow:** When a user uploads a study guide or pastes text, the Application Load Balancer receives the request and routes it to an available Backend Server instance. If multiple students upload documents simultaneously causing a traffic spike, the Auto-Scaling Group automatically provisions additional backend instances to distribute the load without crashing. The backend temporarily stores the raw file in Cloud Object Storage, then orchestrates the data through the AI Processing Module to extract text and generate the requested study materials. Finally, the generated content is saved to the Managed Database for future retrieval, and the results are served back to the user's Frontend securely.

### Components

- **Frontend User Interface**  
  Users can register, log in, upload files, paste notes and view generated outputs. Pages include login, dashboard, upload, result, and history.

- **Application Load Balancer & Auto-Scaling Group**  
  The infrastructure layer that securely routes frontend traffic to the backend and automatically scales the number of backend servers horizontally to maintain performance during high traffic.

- **Backend Server**  
  The core application logic that handles user requests, coordinates data flow, and manages the baseline.

- **AI Processing Module**  
  API responsible for generating summaries, quizzes, flashcards and translations from uploaded documents or pasted content.

- **Database**  
  Used to securely store user profiles, uploaded note metadata, and generated text (summaries, quizzes, flashcards) so users can revisit previously processed materials.

- **Cloud Object Storage**  
  Used to securely store raw uploaded files (such as PDFs or images), ensuring files remain accessible, isolated, and persistent even after the user logs out.

---

## 3. Schedule

| Week | Milestone | Tasks |
|---|---|---|
| Week 11 | Project Kickoff & Proposal | Finalise N-tier architecture design, assign component ownership, submit proposal |
| Week 12 (Phase 1) | Infrastructure & Core Backend | Provision VPC, ALB, Auto-Scaling Group, and EC2 instances; set up cloud object storage (S3) and managed database; implement user authentication (register/login) |
| Week 12 (Phase 2) | Frontend & AI Pipeline | Build frontend pages (login, dashboard, upload, result, history); implement AI processing module — text extraction, summarisation, quiz/flashcard generation, translation |
| Week 13 (Phase 1) | Integration, Scaling & Security | Connect frontend to backend through ALB; configure auto-scaling policies and health checks; end-to-end testing; security hardening (HTTPS, IAM policies, encryption at rest, input validation) |
| Week 13 (Phase 2) | Demo & Submission | Record video demo showcasing full user flow and cloud features; write project report; final code cleanup and documentation; submit all materials |

---

## 4. Team Members and Roles

| SN | Name of Team Member | Student ID | Responsible Components |
|---|---|---|---|
| 1 | Leo Yew Siang, Branson | 2301321 | Backend & AI Engineer |
| 2 | Chiu Jun Jie | 2301524 | Technical PM |
| 3 | Chua Sheng Kai Jovan | 2301244 | Frontend Developer |
| 4 | Cheong Jia Zen | 2301549 | Data & Security Engineer |
