/** How a role sits in MASCO (Malaysia Standard Classification of Occupations, https://emasco.mohr.gov.my). */
/** A minor unit group under a unit group, as eMASCO describes it (translated and condensed from its Malay page). */
export interface MascoMinor {
  name: string;
  /** Its page on eMASCO is /masco/<id>. */
  id: string;
  about: string;
  tasks: string[];
}

/** The unit group itself, as eMASCO describes it (translated and condensed from its Malay page). */
export interface MascoUnit {
  about: string;
  tasks: string[];
  /** Basic salary for a degree holder, from eMASCO's starting salary guide. */
  degreeSalary: string;
  /** Yearly salary increment. */
  increment: string;
}

export interface MascoRole {
  /** The unit group's own details, shown when its box is picked. */
  unit?: MascoUnit;
  /** A short description of the job. */
  about: string;
  /** The minor unit groups under this role's unit group, drawn around it. */
  minors?: MascoMinor[];
  /** The role's own page on eMASCO, when it has one: shown as its classification. */
  url?: string;
}

export const EMASCO_URL = 'https://emasco.mohr.gov.my';

export const mascoRoles: Record<string, MascoRole> = {
  '15-1252.00': {
    about: 'Software developers design, build and maintain software: they turn what people need into working programs, test them and keep them running as needs change.',
    minors: [
      {
        name: 'Software Developer',
        id: '2512-01',
        about: 'Designs, develops, tests and maintains software applications or IT systems to meet the needs of an organisation or its customers. Turns business and technical needs into working software, including web, enterprise and database applications, and keeps systems efficient, secure and up to date.',
        tasks: [
          'Gather and analyse business, technical and user needs',
          'Design, build and maintain software applications, systems and databases',
          'Write, review and optimise code',
          'Test, debug and validate software for function, performance and reliability',
          'Integrate applications with other systems, keeping data safe and consistent',
          'Prepare technical documentation and user guides',
          'Monitor performance and roll out updates and improvements',
        ],
      },
      {
        name: 'Information Technology Systems Architect',
        id: '2512-02',
        about: 'Designs, develops and implements robust, scalable IT systems. Builds system architecture, components and interfaces, reviews existing infrastructure and makes sure systems work together. Guides technology planning, especially in major transformation projects, so systems match present and future business needs.',
        tasks: [
          'Identify business and technical needs to shape the system architecture',
          'Draft architecture covering software, hardware, networks, data, modules and interfaces',
          'Assess current infrastructure and new technology for scalability and integration',
          'Oversee the architecture during implementation, integration and validation',
          'Work with stakeholders and technical teams on transformation projects',
          'Keep architecture documentation and frameworks up to date',
        ],
      },
      {
        name: 'Information Systems Executive',
        id: '2512-03',
        about: 'Manages, administers and maintains an organisation’s information systems so they run securely, reliably and efficiently. Plans, implements and supervises IT infrastructure and applications that support business operations, raise productivity and protect data integrity.',
        tasks: [
          'Develop and carry out IT strategy in line with organisational goals',
          'Manage and maintain hardware and software infrastructure',
          'Ensure system security, data protection and policy compliance',
          'Coordinate with vendors and stakeholders on upgrades',
          'Give technical support to end users',
          'Coordinate system testing and validation, and evaluate system performance',
        ],
      },
      {
        name: 'Systems Developer',
        id: '2512-04',
        about: 'Designs, develops, tests and maintains software applications or systems that support an organisation’s operations. Analyses user needs, writes efficient code, combines software components and makes sure systems are secure, reliable and perform well.',
        tasks: [
          'Work with stakeholders to gather and analyse user and system needs',
          'Design, build, maintain and debug applications and systems',
          'Connect applications to databases and other systems',
          'Prepare and run tests to validate systems',
          'Recommend software solutions that improve performance',
          'Maintain, improve and upgrade existing software, and keep technical documentation',
        ],
      },
    ],
    url: `${EMASCO_URL}/masco/2512`,
    unit: {
      about: 'Researches, analyses and evaluates the requirements of existing or new software applications and operating systems, then designs, develops, tests and troubleshoots software to meet them.',
      degreeSalary: 'RM 4,360',
      increment: 'Minimum 6% a year',
      tasks: [
        'Research, analyse and evaluate requirements for software applications and operating systems',
        'Research, design and develop computer software systems',
        'Consult engineering staff on the interface between hardware and software',
        'Develop and direct software testing and validation procedures',
        'Modify existing software to fix errors, adapt it to new hardware, or upgrade interfaces and performance',
        'Direct software programming and the development of documentation',
        'Evaluate, develop, upgrade and document maintenance procedures for operating systems, communication environments and applications',
        'Advise customers on software system maintenance',
        'Improve understanding and coordinate how the work is carried out',
        'Carry out related tasks',
      ],
    },
  },
  '15-2051.00': {
    url: `${EMASCO_URL}/masco/2524-01`,
    about: 'Data scientists collect and clean data, build statistical and machine-learning models, and explain what the results mean for decisions.',
  },
  '15-2031.00': {
    url: `${EMASCO_URL}/masco/2421-02`,
    about: 'Operations research analysts use mathematical and analytical methods to help organisations solve problems, allocate resources and make better decisions.',
  },
  '15-2051.01': {
    url: `${EMASCO_URL}/masco/2543-07`,
    about: 'Business intelligence analysts turn company data into dashboards and reports so teams can see how the business is doing and act on it.',
  },
  '15-1211.00': {
    about: 'Computer systems analysts gather and examine facts about an organisation’s operations, procedures and systems so they can be turned into programs suited to data processing equipment. They also recommend how computers can improve the organisation’s productivity and profitability.',
    url: `${EMASCO_URL}/masco/2511`,
    unit: {
      about: 'Gathers and analyses information about operations, procedures and systems so they can be converted into programs suited to data processing equipment, and recommends how computers can improve the organisation’s productivity and profit.',
      degreeSalary: 'RM 3,250',
      increment: 'Minimum 6% a year',
      tasks: [
        'Prepare program specifications for computer programmers to act on',
        'Research, analyse and assess information technology needs, procedures or customer problems',
        'Develop proposals and plans to improve current or future information systems, and carry them out',
        'Identify and assess inefficiencies, and analyse processes, procedures and work practices to improve performance',
        'Design, undertake and implement system testing projects',
        'Develop functional specifications for system developers',
        'Extend or modify systems to improve workflows for new services',
        'Coordinate and integrate computer systems within the organisation for operational efficiency',
        'Improve understanding and coordinate how the work is carried out',
        'Perform related tasks',
      ],
    },
    minors: [
      {
        name: 'Management Information Systems (MIS) Analyst',
        id: '2511-01',
        about: 'Designs, develops and improves information systems that collect, process and analyse business data for reporting and decision-making. Implements and maintains MIS solutions, produces reports and dashboards, ensures data accuracy and recommends system improvements.',
        tasks: [
          'Collect and analyse organisational data to support business decisions',
          'Design, develop, improve and maintain management information systems, including automated reports and dashboards',
          'Define user requirements for MIS solutions with business stakeholders',
          'Keep data accurate, complete and consistent across systems and databases',
          'Monitor system performance and resolve technical or data issues',
          'Prepare and present reports, dashboards and analysis',
          'Manage the data sources used for analysis and reporting',
          'Give user support and training on MIS tools and platforms',
        ],
      },
      {
        name: 'Technical Specialist (.Net)',
        id: '2511-02',
        about: 'Designs, develops and maintains software applications on the Microsoft .NET framework. Turns business and user requirements into working solutions, gives technical guidance and makes sure systems are well integrated, high-performing and reliable. Also resolves technical issues and optimises backend services.',
        tasks: [
          'Analyse business and user requirements to decide system functions and technical solutions',
          'Design and develop .NET applications, web components and scalable systems',
          'Prepare technical specifications, designs and documentation',
          'Work with developers, engineers and stakeholders to integrate and implement systems',
          'Test, debug and verify software for function, quality and compatibility',
          'Maintain, update and troubleshoot existing .NET applications',
          'Recommend improvements that optimise performance',
          'Manage system configuration and software upgrades, and monitor performance after deployment',
        ],
      },
      {
        name: 'Register Transfer Level (RTL) Designer',
        id: '2511-03',
        about: 'Designs and implements digital circuits or systems using hardware description languages. Develops high-performance, energy-efficient logic designs that meet functional and timing requirements, working with system architects, verification teams and other engineers.',
        tasks: [
          'Analyse system requirements and architecture to design digital hardware at the RTL level',
          'Write and maintain RTL code in hardware description languages',
          'Develop and optimise the microarchitecture of digital systems and integrated circuits',
          'Simulate and verify designs',
          'Analyse timing reports and ensure timing closure',
          'Integrate modules into larger chip or system-on-chip designs',
          'Debug hardware design issues during development, testing and integration',
          'Join design reviews, and keep technical documentation up to date',
        ],
      },
      {
        name: 'Design Engineer (Information Technology)',
        id: '2511-04',
        about: 'Researches, designs and develops computer software, network systems and utility programs for users and organisations. Analyses requirements and applies computer science, engineering and mathematics to create, improve and maintain software, system architecture and hardware components.',
        tasks: [
          'Research and analyse IT requirements, user needs and system problems',
          'Design and develop system or software prototypes',
          'Simulate, test and validate system performance and reliability',
          'Prepare program specifications, design documents and technical documentation',
          'Propose improvements to existing or future information systems',
          'Work with software developers and technical teams to refine and implement designs',
          'Make sure designs meet technical, quality, security and organisational standards',
        ],
      },
      {
        name: 'Systems Analyst',
        id: '2511-05',
        about: 'Analyses business, technical and data-processing requirements to design, develop and maintain IT systems or applications. Gathers and documents user and system requirements, assesses complex system and network issues, makes system changes and tests new functions so solutions are efficient, reliable and fit business goals.',
        tasks: [
          'Gather and document business and user requirements through interviews and workshops',
          'Analyse information systems, workflows and processes to find issues and suitable solutions',
          'Prepare system documentation and program specifications for developers',
          'Work with developers, testers, UX teams and business users on solutions',
          'Propose improvements to current or future information systems',
          'Run system testing, including user acceptance testing',
          'Support integration with platforms such as ERP, CRM or e-commerce systems',
          'Monitor performance after rollout and coordinate improvements',
        ],
      },
      {
        name: 'Technology Innovation Analyst',
        id: '2511-06',
        about: 'Researches and evaluates new technologies to develop and put in place innovative hardware and software solutions. Finds technology-based opportunities to improve business operations, designs digital tools and makes sure new systems fit into organisational workflows.',
        tasks: [
          'Research new technologies and digital solutions to spot trends and innovation opportunities',
          'Identify technology opportunities that improve operations, systems and workflows',
          'Run feasibility studies and assess the impact of proposed initiatives',
          'Analyse IT requirements, procedures and user problems to find suitable solutions',
          'Work with IT and business teams to plan and implement solutions',
          'Monitor rollout and adoption of new technologies',
          'Evaluate existing systems for inefficiencies and propose improvements',
          'Assess business impact, prepare evaluation reports and support adoption',
        ],
      },
      {
        name: 'Digital Analyst',
        id: '2511-07',
        about: 'Analyses data from websites, mobile apps, search platforms and other digital channels to evaluate online performance and user behaviour. Interprets digital marketing data, assesses campaign effectiveness and finds trends, weaknesses and opportunities to improve visibility, engagement and return on investment.',
        tasks: [
          'Collect and analyse data from websites, apps and digital campaigns, and track traffic, engagement and conversions',
          'Plan, run and optimise digital and search engine marketing campaigns',
          'Prepare reports, dashboards and insights for decision-making',
          'Find inefficiencies in campaigns, systems and processes, and recommend improvements',
          'Work with marketing, content, design and IT teams',
        ],
      },
      {
        name: 'Digital Transformation Executive/Officer',
        id: '2511-08',
        about: 'Leads and coordinates initiatives that drive digital change in line with business objectives. Facilitates business requirement discussions, plans and manages cross-functional projects, develops budgets and operational plans, and tracks progress through structured reporting.',
        tasks: [
          'Facilitate and analyse business requirement discussions for digital transformation',
          'Assess the organisation’s IT needs, existing systems and user challenges',
          'Analyse business processes for inefficiencies and room to improve',
          'Plan and carry out improvements to information systems and digital workflows',
          'Prepare project documentation, implementation records and reports',
          'Coordinate rollout of digital solutions across functions and track progress',
          'Communicate with stakeholders throughout transformation projects',
          'Assess project risks and plan how to reduce them',
        ],
      },
      {
        name: 'Service Desk Specialist',
        id: '2511-09',
        about: 'Gives first-level technical support to users by handling service requests, diagnosing and fixing problems with computer systems and applications, and passing complex cases to the right teams. Monitors incidents and keeps accurate records so IT services stay available.',
        tasks: [
          'Answer user queries and incidents by phone, email, chat or on site',
          'Record and track service requests and incidents in a ticketing system',
          'Diagnose and fix basic hardware, software and network issues',
          'Escalate unresolved or complex issues to higher-level support',
          'Keep users updated on progress',
          'Document fixes and update the knowledge base',
          'Spot recurring issues for follow-up',
          'Prepare reports on service desk activity and performance',
        ],
      },
      {
        name: 'Vendor Management Analyst (Information Technology)',
        id: '2511-10',
        about: 'Manages relationships with external IT vendors so third-party services meet the organisation’s requirements and contract terms. Evaluates and selects vendors, monitors performance and compliance, negotiates terms and reduces the risks of outsourced IT services, working with procurement, legal and IT teams.',
        tasks: [
          'Research, evaluate and recommend IT vendors, products and services',
          'Review, negotiate and manage vendor contracts and service level agreements',
          'Monitor vendor performance and compliance with contracts, policies and regulations',
          'Keep accurate records of vendor contracts and agreements',
          'Support vendor risk management and governance',
          'Work with internal departments to align vendor services with business needs',
          'Help resolve issues with vendor products and services',
          'Analyse vendor management processes and recommend improvements',
        ],
      },
    ],
  },
  '15-1212.00': { about: 'Information security analysts plan and carry out measures that protect an organisation’s networks and data from attacks.' },
  '15-1232.00': { about: 'Computer user support specialists help people with their hardware, software and accounts, fixing problems and explaining how things work.' },
  '15-1255.00': { about: 'Web and digital interface designers plan and build how websites and apps look and feel, so they are clear and easy to use.' },
};
