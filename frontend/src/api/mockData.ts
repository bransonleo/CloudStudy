import type { BackendMaterial } from '../types';

export const mockMaterial: BackendMaterial = {
  material_id: 'mock-001',
  filename: 'sample-notes.pdf',
  status: 'ready',
  error_message: null,
  results: {
    summary: {
      status: 'done',
      content: {
        title: 'Cloud Computing Fundamentals',
        key_points: [
          'IaaS, PaaS, and SaaS are the three main cloud service models',
          'Horizontal scaling adds more servers; vertical scaling adds resources to one server',
          'Application Load Balancers distribute traffic across backend instances',
          'Auto-scaling adjusts compute capacity based on demand',
          'Multi-AZ deployment provides high availability and fault tolerance',
        ],
        summary:
          'This document covers the fundamentals of cloud computing, including Infrastructure as a Service (IaaS), Platform as a Service (PaaS), and Software as a Service (SaaS). Key topics include virtualization, horizontal vs vertical scaling, load balancing, and auto-scaling groups. The document also discusses the shared responsibility model in cloud security and best practices for designing fault-tolerant architectures using multiple availability zones.',
      },
    },
    quiz: {
      status: 'done',
      content: {
        questions: [
          {
            question: 'Which cloud service model provides the most control over infrastructure?',
            options: ['SaaS', 'PaaS', 'IaaS', 'FaaS'],
            correct_index: 2,
            explanation: 'IaaS gives you control over the OS, storage, and networking, unlike PaaS or SaaS which abstract those layers.',
          },
          {
            question: 'What is the primary purpose of an Application Load Balancer?',
            options: [
              'Store files in the cloud',
              'Distribute incoming traffic across multiple targets',
              'Manage database connections',
              'Encrypt data at rest',
            ],
            correct_index: 1,
            explanation: 'An ALB distributes incoming HTTP/HTTPS traffic across multiple registered targets to ensure no single instance is overwhelmed.',
          },
          {
            question: 'What does horizontal scaling mean?',
            options: [
              'Adding more CPU/RAM to a single server',
              'Adding more servers to handle load',
              'Increasing storage capacity',
              'Upgrading the operating system',
            ],
            correct_index: 1,
            explanation: 'Horizontal scaling (scaling out) means adding more instances, as opposed to vertical scaling (scaling up) which upgrades a single instance.',
          },
          {
            question: 'Which AWS service provides managed relational databases?',
            options: ['S3', 'EC2', 'RDS', 'Lambda'],
            correct_index: 2,
            explanation: 'Amazon RDS (Relational Database Service) manages databases like MySQL, PostgreSQL, and others, handling backups, patching, and failover.',
          },
          {
            question: 'What is the benefit of multi-AZ deployment?',
            options: [
              'Lower cost',
              'Faster CPU performance',
              'High availability and fault tolerance',
              'Larger storage capacity',
            ],
            correct_index: 2,
            explanation: 'Deploying across multiple Availability Zones ensures your application stays available even if one data center experiences an outage.',
          },
        ],
      },
    },
    flashcards: {
      status: 'done',
      content: {
        flashcards: [
          { front: 'What is IaaS?', back: 'Infrastructure as a Service — provides virtualized computing resources over the internet (e.g., EC2, virtual machines).' },
          { front: 'What is auto-scaling?', back: 'Automatically adjusting the number of compute instances based on current demand to maintain performance and minimize cost.' },
          { front: 'What is an Availability Zone?', back: 'A physically separate data center within an AWS Region, providing redundancy and fault tolerance.' },
          { front: 'What is S3?', back: 'Simple Storage Service — an object storage service for storing and retrieving any amount of data at any time.' },
          { front: 'What is the Shared Responsibility Model?', back: 'AWS manages security OF the cloud (infrastructure), while customers manage security IN the cloud (data, access, applications).' },
        ],
      },
    },
  },
};
