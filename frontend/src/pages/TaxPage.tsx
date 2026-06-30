import { SingletonFormPage } from '@/components/pages/SingletonFormPage'
import type { FormConfig } from '@/components/form/types'
import type { TaxAssumption } from '@/types'
import { taxFrequencyOptions } from '@/utils/options'

const config: FormConfig = [
  {
    title: 'Corporate Tax',
    icon: '⊞',
    fields: [
      { name: 'corporate_tax_enabled', label: 'Corporate tax enabled', kind: 'switch' },
      { name: 'corporate_tax_rate', label: 'Corporate Tax Rate', kind: 'percent', visibleWhen: (v) => v.corporate_tax_enabled !== false, requiredWhen: (v) => v.corporate_tax_enabled !== false, help: 'Required when corporate tax is enabled. A 0% rate means no income tax expense is modelled.' },
      { name: 'tax_payment_frequency', label: 'Tax Payment Frequency', kind: 'select', options: taxFrequencyOptions, visibleWhen: (v) => v.corporate_tax_enabled !== false },
      { name: 'tax_loss_carryforward_enabled', label: 'Tax Loss Carryforward', kind: 'switch', help: 'Allow losses to offset future taxable profits.' },
      { name: 'withholding_tax_rate', label: 'Withholding Tax Rate', kind: 'percent' },
      { name: 'zakat_rate', label: 'Zakat Rate (optional)', kind: 'percent' },
    ],
  },
  {
    title: 'VAT / Sales Tax',
    icon: '◷',
    fields: [
      { name: 'vat_enabled', label: 'VAT system enabled', kind: 'switch' },
      { name: 'vat_rate', label: 'Default VAT rate', kind: 'percent', visibleWhen: (v) => v.vat_enabled !== false, requiredWhen: (v) => v.vat_enabled !== false, help: 'The VAT rate applied to items marked VAT-applicable. Line-level VAT switches on Direct Costs, Operating Expenses and Fixed Assets only flag whether an item is subject to VAT — they do not set the rate.' },
      { name: 'vat_registration_threshold', label: 'VAT Registration Threshold', kind: 'currency', visibleWhen: (v) => v.vat_enabled !== false, help: 'Revenue level above which VAT registration is required.' },
      { name: 'vat_payment_frequency', label: 'VAT Payment Frequency', kind: 'select', options: taxFrequencyOptions, visibleWhen: (v) => v.vat_enabled !== false },
    ],
  },
  {
    title: 'Duties & Regulatory Fees',
    advanced: true,
    fields: [
      { name: 'customs_duty_rate', label: 'Customs Duty Rate', kind: 'percent' },
      { name: 'municipality_fees', label: 'Municipality Fees', kind: 'currency' },
      { name: 'license_renewal_fees', label: 'License Renewal Fees', kind: 'currency' },
    ],
  },
  {
    title: 'Payroll Compliance',
    advanced: true,
    fields: [
      { name: 'employer_social_security_rate', label: 'Employer Social Security % (global default)', kind: 'percent', help: 'Default employer social-security rate applied to every staffing role. A role can override this on the Staffing page.' },
      { name: 'employee_social_security_rate', label: 'Employee Social Security %', kind: 'percent', help: 'Employee-side contribution (informational; deducted from employees, not an employer cost).' },
    ],
  },
]

export function TaxPage() {
  return (
    <SingletonFormPage<TaxAssumption>
      slug="tax"
      sectionKey="tax"
      config={config}
      renderBottom={(v) => {
        const corpZero = v.corporate_tax_enabled !== false && !(Number(v.corporate_tax_rate) > 0)
        const vatZero = v.vat_enabled !== false && !(Number(v.vat_rate) > 0)
        if (!corpZero && !vatZero) return null
        return (
          <div className="banner banner--warning">
            <span className="banner__icon">⚠</span>
            <div>
              {corpZero && <div>Corporate tax is enabled but the rate is 0% — no income tax expense will be modelled.</div>}
              {vatZero && <div>VAT is enabled but the default rate is 0% — no VAT will be applied to VAT-applicable items.</div>}
            </div>
          </div>
        )
      }}
    />
  )
}
