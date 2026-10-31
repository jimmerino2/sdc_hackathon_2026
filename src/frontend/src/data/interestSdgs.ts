/** One SDG target, like 2.1. */
export interface SdgTarget {
  code: string;
  text: string;
}

/** One goal an interest connects to, with the targets behind it. */
export interface InterestSdg {
  sdg: number;
  targets: SdgTarget[];
}

/** Each goal's title and text colour: the UN colour, darkened where needed to stay readable on white. */
export const SDG_GOALS: Record<number, { title: string; color: string }> = {
  1: { title: 'No Poverty', color: '#e5243b' },
  2: { title: 'Zero Hunger', color: '#957027' },
  3: { title: 'Good Health and Well-being', color: '#3f852f' },
  4: { title: 'Quality Education', color: '#c5192d' },
  5: { title: 'Gender Equality', color: '#e0331d' },
  6: { title: 'Clean Water and Sanitation', color: '#0a8bb0' },
  7: { title: 'Affordable and Clean Energy', color: '#9a7200' },
  8: { title: 'Decent Work and Economic Growth', color: '#a21942' },
  9: { title: 'Industry, Innovation and Infrastructure', color: '#c7521d' },
  10: { title: 'Reduced Inequalities', color: '#dd1367' },
  11: { title: 'Sustainable Cities and Communities', color: '#a86818' },
  12: { title: 'Responsible Consumption and Production', color: '#996f25' },
  13: { title: 'Climate Action', color: '#3f7e44' },
  14: { title: 'Life Below Water', color: '#087eb5' },
  15: { title: 'Life on Land', color: '#3c861e' },
  16: { title: 'Peace, Justice and Strong Institutions', color: '#00689d' },
  17: { title: 'Partnerships for the Goals', color: '#19486a' },
};

/** The goals and targets shown for each interest, keyed by the interest's name. */
export const INTEREST_SDGS: Record<string, InterestSdg[]> = {
  'Cooking & Baking': [
    { sdg: 2, targets: [
      { code: '2.1', text: 'Access to safe, nutritious and sufficient food.' },
      { code: '2.4', text: 'Sustainable food production and resilient agricultural practices.' },
    ] },
    { sdg: 12, targets: [
      { code: '12.3', text: 'Reduce food waste at retail and consumer levels.' },
      { code: '12.8', text: 'Ensure people have information and awareness for sustainable lifestyles.' },
    ] },
    { sdg: 3, targets: [
      { code: '3.4', text: 'Promote mental health and well-being and reduce premature mortality from non-communicable diseases.' },
    ] },
  ],
  'Gardening & Farming': [
    { sdg: 2, targets: [
      { code: '2.3', text: 'Increase agricultural productivity and incomes of small-scale food producers.' },
      { code: '2.4', text: 'Implement sustainable and resilient agricultural practices.' },
    ] },
    { sdg: 15, targets: [
      { code: '15.1', text: 'Conserve and restore terrestrial and inland freshwater ecosystems.' },
      { code: '15.3', text: 'Combat desertification and restore degraded land and soil.' },
    ] },
    { sdg: 13, targets: [
      { code: '13.3', text: 'Improve education and awareness of climate change mitigation and adaptation.' },
    ] },
  ],
  'Sports & Fitness': [
    { sdg: 3, targets: [
      { code: '3.4', text: 'Promote mental health and well-being.' },
      { code: '3.5', text: 'Strengthen prevention and treatment of substance abuse.' },
    ] },
    { sdg: 5, targets: [
      { code: '5.1', text: 'End all forms of discrimination against women and girls.' },
      { code: '5.5', text: 'Ensure women’s full and effective participation and equal leadership opportunities.' },
    ] },
    { sdg: 10, targets: [
      { code: '10.2', text: 'Promote social, economic and political inclusion for all.' },
    ] },
  ],
  'Music, Art & Performance': [
    { sdg: 4, targets: [
      { code: '4.7', text: 'Promote education for sustainable development, global citizenship and appreciation of cultural diversity.' },
    ] },
    { sdg: 11, targets: [
      { code: '11.4', text: 'Strengthen efforts to protect and safeguard cultural and natural heritage.' },
    ] },
    { sdg: 8, targets: [
      { code: '8.3', text: 'Promote entrepreneurship, creativity, innovation and the growth of micro, small and medium enterprises.' },
    ] },
  ],
  'Design & Making': [
    { sdg: 9, targets: [
      { code: '9.5', text: 'Enhance scientific research and technological capabilities.' },
      { code: '9.4', text: 'Upgrade infrastructure and industries to make them sustainable.' },
    ] },
    { sdg: 12, targets: [
      { code: '12.5', text: 'Substantially reduce waste generation through prevention, reduction, recycling and reuse.' },
      { code: '12.2', text: 'Achieve sustainable management and efficient use of natural resources.' },
    ] },
    { sdg: 8, targets: [
      { code: '8.3', text: 'Support productive activities, entrepreneurship, creativity and innovation.' },
    ] },
  ],
  'Charity & Volunteering': [
    { sdg: 1, targets: [
      { code: '1.2', text: 'Reduce poverty in all its dimensions.' },
      { code: '1.3', text: 'Implement social protection systems for all.' },
    ] },
    { sdg: 10, targets: [
      { code: '10.2', text: 'Promote social, economic and political inclusion.' },
      { code: '10.3', text: 'Ensure equal opportunities and reduce inequalities of outcome.' },
    ] },
    { sdg: 17, targets: [
      { code: '17.17', text: 'Encourage effective partnerships between public, private and civil society organisations.' },
    ] },
  ],
  'Animals & Wildlife': [
    { sdg: 15, targets: [
      { code: '15.5', text: 'Reduce the degradation of natural habitats and halt biodiversity loss.' },
      { code: '15.7', text: 'End poaching and trafficking of protected species.' },
    ] },
    { sdg: 14, targets: [
      { code: '14.2', text: 'Protect and sustainably manage marine and coastal ecosystems.' },
      { code: '14.4', text: 'End overfishing and destructive fishing practices.' },
    ] },
    { sdg: 12, targets: [
      { code: '12.2', text: 'Achieve sustainable management and efficient use of natural resources.' },
      { code: '12.8', text: 'Promote awareness of sustainable lifestyles and harmony with nature.' },
    ] },
  ],
  'Gaming & Coding': [
    { sdg: 4, targets: [
      { code: '4.4', text: 'Increase the number of people with relevant technical and vocational skills.' },
      { code: '4.7', text: 'Promote education for sustainable development and global citizenship.' },
    ] },
    { sdg: 9, targets: [
      { code: '9.5', text: 'Enhance scientific research and technological capabilities.' },
      { code: '9.c', text: 'Increase access to information and communications technology.' },
    ] },
    { sdg: 8, targets: [
      { code: '8.2', text: 'Achieve higher economic productivity through technological upgrading and innovation.' },
      { code: '8.3', text: 'Support entrepreneurship and innovation.' },
    ] },
  ],
  'Teaching & Mentoring': [
    { sdg: 4, targets: [
      { code: '4.1', text: 'Ensure inclusive and equitable quality education.' },
      { code: '4.4', text: 'Increase relevant technical and vocational skills.' },
      { code: '4.5', text: 'Eliminate disparities in education.' },
    ] },
    { sdg: 10, targets: [
      { code: '10.2', text: 'Promote social and economic inclusion for all.' },
    ] },
    { sdg: 5, targets: [
      { code: '5.1', text: 'End all forms of discrimination against women and girls.' },
      { code: '5.5', text: 'Ensure equal opportunities for leadership and participation.' },
    ] },
  ],
  'Fashion & Thrifting': [
    { sdg: 12, targets: [
      { code: '12.2', text: 'Achieve sustainable management and efficient use of natural resources.' },
      { code: '12.5', text: 'Reduce waste through prevention, recycling and reuse.' },
      { code: '12.8', text: 'Promote awareness of sustainable lifestyles.' },
    ] },
    { sdg: 8, targets: [
      { code: '8.7', text: 'Eradicate forced labour, modern slavery and child labour.' },
      { code: '8.8', text: 'Protect labour rights and promote safe working environments.' },
    ] },
    { sdg: 13, targets: [
      { code: '13.3', text: 'Improve education and awareness of climate change mitigation and adaptation.' },
    ] },
  ],
  'Fixing & Building': [
    { sdg: 9, targets: [
      { code: '9.1', text: 'Develop quality, reliable, sustainable and resilient infrastructure.' },
      { code: '9.4', text: 'Upgrade infrastructure and industries for sustainability.' },
    ] },
    { sdg: 11, targets: [
      { code: '11.3', text: 'Promote inclusive and sustainable urbanisation.' },
      { code: '11.6', text: 'Reduce the environmental impact of cities.' },
    ] },
    { sdg: 12, targets: [
      { code: '12.5', text: 'Reduce waste through prevention, recycling and reuse.' },
      { code: '12.2', text: 'Use natural resources sustainably.' },
    ] },
  ],
  'Mental Health & Wellness': [
    { sdg: 3, targets: [
      { code: '3.4', text: 'Promote mental health and well-being.' },
      { code: '3.5', text: 'Strengthen prevention and treatment of substance abuse.' },
      { code: '3.8', text: 'Achieve universal health coverage.' },
    ] },
    { sdg: 10, targets: [
      { code: '10.2', text: 'Promote social, economic and political inclusion.' },
    ] },
    { sdg: 4, targets: [
      { code: '4.7', text: 'Promote education for sustainable development, human rights and global citizenship.' },
    ] },
  ],
  'Nature & Outdoors': [
    { sdg: 15, targets: [
      { code: '15.1', text: 'Conserve and restore terrestrial and freshwater ecosystems.' },
      { code: '15.5', text: 'Reduce habitat degradation and biodiversity loss.' },
    ] },
    { sdg: 13, targets: [
      { code: '13.3', text: 'Improve education and awareness of climate change.' },
    ] },
    { sdg: 14, targets: [
      { code: '14.1', text: 'Prevent and significantly reduce marine pollution.' },
      { code: '14.2', text: 'Protect and restore marine and coastal ecosystems.' },
    ] },
  ],
  'Money & Starting a Business': [
    { sdg: 8, targets: [
      { code: '8.3', text: 'Promote entrepreneurship and the growth of small and medium enterprises.' },
      { code: '8.5', text: 'Achieve full and productive employment and decent work for all.' },
    ] },
    { sdg: 9, targets: [
      { code: '9.3', text: 'Increase access to financial services and markets for small enterprises.' },
      { code: '9.5', text: 'Enhance research and technological innovation.' },
    ] },
    { sdg: 1, targets: [
      { code: '1.4', text: 'Ensure equal rights to economic resources and access to financial services.' },
    ] },
  ],
  'Politics & Community Issues': [
    { sdg: 16, targets: [
      { code: '16.6', text: 'Develop effective, accountable and transparent institutions.' },
      { code: '16.7', text: 'Ensure responsive, inclusive, participatory and representative decision-making.' },
      { code: '16.10', text: 'Ensure public access to information and protect fundamental freedoms.' },
    ] },
    { sdg: 10, targets: [
      { code: '10.2', text: 'Promote social, economic and political inclusion.' },
      { code: '10.3', text: 'Ensure equal opportunities and reduce inequalities.' },
    ] },
    { sdg: 11, targets: [
      { code: '11.3', text: 'Enhance inclusive and sustainable urbanisation and participatory planning.' },
      { code: '11.7', text: 'Provide universal access to safe, inclusive and accessible public spaces.' },
    ] },
  ],
};
