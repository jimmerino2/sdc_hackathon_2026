/** Display names for the units the /outlook API reports by code. */

export const COUNTRIES: Record<string, string> = {
  AU: 'Australia', CA: 'Canada', DE: 'Germany', FR: 'France', GB: 'United Kingdom', IE: 'Ireland', IT: 'Italy',
  NL: 'Netherlands', US: 'United States',
};

/** NAICS sectors as used by Census BTOS ("US" = all businesses). */
export const SECTORS: Record<string, string> = {
  US: 'All US businesses', '11': 'Agriculture, forestry & fishing', '21': 'Mining, oil & gas', '22': 'Utilities',
  '23': 'Construction', '31': 'Manufacturing', '42': 'Wholesale trade', '44': 'Retail trade',
  '48': 'Transportation & warehousing', '51': 'Information', '52': 'Finance & insurance', '53': 'Real estate',
  '54': 'Professional, scientific & technical', '55': 'Management of companies', '56': 'Admin & support services',
  '61': 'Educational services', '62': 'Health care & social assistance', '71': 'Arts & recreation',
  '72': 'Accommodation & food', '81': 'Other services',
};

/** 2018 SOC major groups ("00" = all workers). */
export const OCCUPATIONS: Record<string, string> = {
  '00': 'All workers', '11': 'Management', '13': 'Business & financial', '15': 'Computer & mathematical',
  '17': 'Architecture & engineering', '19': 'Life, physical & social science', '21': 'Community & social service',
  '23': 'Legal', '25': 'Education & library', '27': 'Arts, design, media & sports', '29': 'Healthcare practitioners',
  '31': 'Healthcare support', '33': 'Protective service', '35': 'Food preparation & serving',
  '37': 'Building & grounds maintenance', '39': 'Personal care & service', '41': 'Sales',
  '43': 'Office & administrative support', '45': 'Farming, fishing & forestry', '47': 'Construction & extraction',
  '49': 'Installation, maintenance & repair', '51': 'Production', '53': 'Transportation & material moving',
};
