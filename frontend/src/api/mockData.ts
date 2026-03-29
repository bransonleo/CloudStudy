import type { MaterialResult } from '../types';

export const mockResult: MaterialResult = {
  material_id: 'mock-001',
  filename: 'sample-notes.pdf',
  created_at: new Date().toISOString(),
  summary:
    'This document covers the fundamentals of cloud computing, including Infrastructure as a Service (IaaS), Platform as a Service (PaaS), and Software as a Service (SaaS). Key topics include virtualization, horizontal vs vertical scaling, load balancing, and auto-scaling groups. The document also discusses the shared responsibility model in cloud security and best practices for designing fault-tolerant architectures using multiple availability zones.',
  quiz: [
    {
      question: 'Which cloud service model provides the most control over infrastructure?',
      options: ['SaaS', 'PaaS', 'IaaS', 'FaaS'],
      correct_index: 2,
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
    },
    {
      question: 'Which AWS service provides managed relational databases?',
      options: ['S3', 'EC2', 'RDS', 'Lambda'],
      correct_index: 2,
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
    },
  ],
  flashcards: [
    { front: 'What is IaaS?', back: 'Infrastructure as a Service — provides virtualized computing resources over the internet (e.g., EC2, virtual machines).' },
    { front: 'What is auto-scaling?', back: 'Automatically adjusting the number of compute instances based on current demand to maintain performance and minimize cost.' },
    { front: 'What is an Availability Zone?', back: 'A physically separate data center within an AWS Region, providing redundancy and fault tolerance.' },
    { front: 'What is S3?', back: 'Simple Storage Service — an object storage service for storing and retrieving any amount of data at any time.' },
    { front: 'What is the Shared Responsibility Model?', back: 'AWS manages security OF the cloud (infrastructure), while customers manage security IN the cloud (data, access, applications).' },
  ],
  translation:
    'Este documento cubre los fundamentos de la computación en la nube, incluyendo Infraestructura como Servicio (IaaS), Plataforma como Servicio (PaaS) y Software como Servicio (SaaS). Los temas clave incluyen virtualización, escalado horizontal vs vertical, balanceo de carga y grupos de autoescalado.',
};
