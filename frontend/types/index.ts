export type UUID = string;

export interface Me {
  id: UUID;
  organization_id: UUID;
  full_name: string;
  email: string;
  role: "super_admin" | "spa_admin" | "staff";
  is_active: boolean;
  created_at: string;
}

export interface DashboardSummary {
  new_leads_today: number;
  contacted_today: number;
  booked_today: number;
  escalated_today: number;
  avg_first_response_seconds: number | null;
  inbox_open: number;
  conversations_handled_7d: number;
  missed_calls_recovered_7d: number;
  booking_links_sent_7d: number;
  booked_7d: number;
  ai_handled_pct_7d: number | null;
}

export interface Lead {
  id: UUID;
  organization_id: UUID;
  location_id: UUID | null;
  source_type: string;
  source_label: string | null;
  first_name: string | null;
  last_name: string | null;
  full_name: string | null;
  phone: string | null;
  email: string | null;
  preferred_contact_method: string | null;
  treatment_interest: string | null;
  status: string;
  lifecycle_stage: string;
  booking_status: string;
  do_not_contact: boolean;
  assigned_to_user_id: UUID | null;
  notes: string | null;
  last_inbound_at: string | null;
  last_outbound_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: UUID;
  organization_id: UUID;
  lead_id: UUID;
  channel_type: string;
  status: string;
  ai_enabled: boolean;
  escalation_state: string;
  ai_mode: "active" | "paused" | "escalated";
  created_at: string;
  updated_at: string;
}

export interface ConversationListItem extends Conversation {
  lead_name: string | null;
  lead_phone: string | null;
  last_message_preview: string | null;
  last_message_at: string | null;
  unread_from_lead: boolean;
}

export interface Message {
  id: UUID;
  conversation_id: UUID;
  lead_id: UUID;
  direction: "inbound" | "outbound" | "internal_note";
  sender_type: "lead" | "system" | "ai" | "staff";
  channel_type: string;
  content: string;
  delivery_status: string;
  ai_generated: boolean;
  reviewed_by_human: boolean;
  created_at: string;
}

export interface ConversationDetail extends Conversation {
  lead: Lead;
  messages: Message[];
}

export interface FAQ {
  id: UUID;
  organization_id: UUID;
  location_id: UUID | null;
  category: string;
  question: string;
  answer: string;
  tags: string[] | null;
  is_active: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface BookingRoute {
  id: UUID;
  organization_id: UUID;
  location_id: UUID | null;
  treatment_name: string;
  normalized_treatment_key: string;
  route_type: "consult" | "direct_booking" | "callback";
  booking_url: string | null;
  fallback_message: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AutomationRule {
  id: UUID;
  organization_id: UUID;
  name: string;
  trigger_event: string;
  channel_type: string;
  is_active: boolean;
  delay_minutes: number;
  template_id: UUID | null;
  conditions: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface MessageTemplate {
  id: UUID;
  organization_id: UUID;
  name: string;
  template_type: string;
  content: string;
  variables: Record<string, unknown> | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OrgSettings {
  id: UUID;
  organization_id: UUID;
  brand_name: string;
  default_location_id: UUID | null;
  tone_of_voice: string;
  disclaimers: string;
  escalation_message: string;
  booking_cta_style: string;
  ai_enabled: boolean;
  auto_send_replies: boolean;
  collect_name: boolean;
  collect_email: boolean;
  collect_treatment_interest: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export type BillingStatus = {
  subscription_status: "trialing" | "active" | "past_due" | "cancelled";
  lemon_subscription_id: string | null;
  trial_ends_at: string | null;
};
