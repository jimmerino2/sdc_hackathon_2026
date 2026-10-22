-- Gives each role an icon the frontend can render: a Lucide icon name in kebab-case (https://lucide.dev/icons).
-- load_supabase.py upserts only the CSV's columns, so reloading onet_roles keeps these values.
alter table public.onet_roles
    add column icon text not null default 'briefcase' check (icon ~ '^[a-z0-9]+(-[a-z0-9]+)*$');

update public.onet_roles as r
set icon = v.icon
from (values
    ('11-2021.00', 'megaphone'),        -- Marketing Managers
    ('13-1071.00', 'users'),            -- Human Resources Specialists
    ('13-1081.00', 'boxes'),            -- Logisticians
    ('13-1082.00', 'clipboard-list'),   -- Project Management Specialists
    ('13-1161.00', 'chart-pie'),        -- Market Research Analysts and Marketing Specialists
    ('13-2011.00', 'calculator'),       -- Accountants and Auditors
    ('13-2053.00', 'shield-check'),     -- Insurance Underwriters
    ('13-2072.00', 'landmark'),         -- Loan Officers
    ('15-1211.00', 'monitor'),          -- Computer Systems Analysts
    ('15-1212.00', 'shield'),           -- Information Security Analysts
    ('15-1232.00', 'headset'),          -- Computer User Support Specialists
    ('15-1252.00', 'code'),             -- Software Developers
    ('15-1255.00', 'palette'),          -- Web and Digital Interface Designers
    ('15-2031.00', 'sigma'),            -- Operations Research Analysts
    ('15-2051.00', 'brain'),            -- Data Scientists
    ('15-2051.01', 'chart-bar'),        -- Business Intelligence Analysts
    ('17-2071.00', 'zap'),              -- Electrical Engineers
    ('17-2081.00', 'leaf'),             -- Environmental Engineers
    ('17-2112.00', 'factory'),          -- Industrial Engineers
    ('19-2041.00', 'microscope'),       -- Environmental Scientists and Specialists, Including Health
    ('21-1093.00', 'hand-heart'),       -- Social and Human Service Assistants
    ('23-2011.00', 'scale'),            -- Paralegals and Legal Assistants
    ('25-2011.00', 'baby'),             -- Preschool Teachers
    ('25-2021.00', 'school'),           -- Elementary School Teachers
    ('27-3042.00', 'pen-tool'),         -- Technical Writers
    ('27-3091.00', 'languages'),        -- Interpreters and Translators
    ('29-1123.00', 'activity'),         -- Physical Therapists
    ('29-1141.00', 'stethoscope'),      -- Registered Nurses
    ('29-2052.00', 'pill'),             -- Pharmacy Technicians
    ('29-9021.00', 'clipboard-plus'),   -- Health Information Technologists and Medical Registrars
    ('31-1122.00', 'heart-handshake'),  -- Personal Care Aides
    ('33-9032.00', 'shield-alert'),     -- Security Guards
    ('35-2014.00', 'chef-hat'),         -- Cooks, Restaurant
    ('41-2031.00', 'shopping-bag'),     -- Retail Salespersons
    ('43-3031.00', 'receipt'),          -- Bookkeeping, Accounting, and Auditing Clerks
    ('43-3071.00', 'banknote'),         -- Tellers
    ('43-4051.00', 'headphones'),       -- Customer Service Representatives
    ('43-6014.00', 'briefcase'),        -- Secretaries and Administrative Assistants
    ('43-9021.00', 'keyboard'),         -- Data Entry Keyers
    ('47-2111.00', 'plug'),             -- Electricians
    ('47-2231.00', 'sun'),              -- Solar Photovoltaic Installers
    ('49-9071.00', 'wrench'),           -- Maintenance and Repair Workers, General
    ('49-9081.00', 'wind'),             -- Wind Turbine Service Technicians
    ('51-2022.00', 'cpu'),              -- Electrical and Electronic Equipment Assemblers
    ('53-3032.00', 'truck'),            -- Heavy and Tractor-Trailer Truck Drivers
    ('53-7062.00', 'package')           -- Laborers and Freight, Stock, and Material Movers, Hand
) as v (onet_code, icon)
where r.onet_code = v.onet_code;
