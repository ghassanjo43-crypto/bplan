/* Central registry of contextual help copy for Guided Help mode.
 *
 * Keys are dot-namespaced by area. Add an entry here and reference it from a
 * <HelpTooltip helpKey="..."> anywhere in the UI. Unknown keys resolve to no
 * tooltip (see resolveHelpText), so a typo simply shows nothing rather than
 * throwing. */

export interface HelpEntry {
  /** Optional short heading shown above the explanation (reserved for future use). */
  title?: string
  /** The explanation shown in the tooltip bubble. */
  text: string
}

export const helpContent = {
  'dashboard.overview': {
    title: 'Dashboard',
    text: 'Your workspace home — pick a company and project, track plan completion, and jump into any section of the business plan.',
  },
  'project.setup': {
    title: 'Project Setup',
    text: 'Define the business identity and the structure of your model — currency, projection start date, horizon, and frequency. These settings shape every calculation.',
  },
  'revenue.streams': {
    title: 'Revenue Streams',
    text: 'Define how the business earns money — products, services, subscriptions, or contracts — with pricing, timing, and recurrence for each stream.',
  },
  'revenue.projection': {
    title: 'Revenue Projection',
    text: 'Use this section to enter or review expected revenue by month or year. These figures feed into the income statement and reports.',
  },
  'revenue.growth': {
    title: 'Apply Growth',
    text: 'Applies a percentage increase across future periods. You can apply it to the selected row or all rows.',
  },
  'direct.costs': {
    title: 'Direct Costs',
    text: 'Costs directly tied to delivering your products or services (cost of goods sold). Link each cost to one, many, all, or no revenue streams.',
  },
  'operating.expenses': {
    title: 'Operating Expenses',
    text: 'Ongoing running costs not tied to a specific sale — rent, salaries, marketing, and admin. These reduce operating profit.',
  },
  'income.statement': {
    title: 'Income Statement',
    text: 'The income statement summarizes revenue, costs, profit, and net income over the forecast period.',
  },
  'scenarios': {
    title: 'Scenarios',
    text: 'Scenarios let you compare different business assumptions such as base case, optimistic case, and downside case.',
  },
  'reports': {
    title: 'Reports',
    text: 'Generate an investor-ready business plan document (Word or PDF) or a live Excel financial model from your assumptions and statements.',
  },
  'narrative.editor': {
    title: 'Narrative Editor',
    text: 'Write the written business plan that accompanies your financials — executive summary, market, strategy, risks, and more. Content flows into the exported report.',
  },
  'ai.generateText': {
    title: 'Generate with AI',
    text: 'Draft or refine narrative text with AI using your project data as context. Review and edit generated content before final use.',
  },
} satisfies Record<string, HelpEntry>

export type HelpKey = keyof typeof helpContent
