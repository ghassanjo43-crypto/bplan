/* Types mirroring backend/app/schemas/ai.py */

export type AiLanguage = 'english' | 'arabic'
export type AiTone = 'investor' | 'bank' | 'formal' | 'government' | 'simple' | 'big_four'
export type AiAction =
  | 'generate'
  | 'improve'
  | 'shorten'
  | 'expand'
  | 'translate_arabic'
  | 'translate_english'

export interface AiGenerateRequest {
  section_key?: string | null
  section_title?: string | null
  user_prompt: string
  language: AiLanguage
  tone: AiTone
  action: AiAction
  current_text?: string | null
}

export interface AiGenerateResponse {
  content: string
  language: AiLanguage
  action: AiAction
  provider: string
  model: string
}
