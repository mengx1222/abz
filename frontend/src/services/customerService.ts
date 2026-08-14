import api from './api';
import { useAuthStore } from '../stores/authStore';

// ----------- Types -----------

export interface Customer {
  id: string;
  name: string;
  age: number | null;
  gender: 'male' | 'female' | null;
  phone: string | null;
  customer_type: 'prospective' | 'active' | 'lapsed';
  tags: string[] | null;
  insurance_type: string | null;
  current_stage: string;
  intention_level: number;
  source_channel: string | null;
  notes: string | null;
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
}

export interface Interaction {
  id: string;
  customer_id: string;
  type: 'phone' | 'wechat' | 'f2f' | 'email' | 'other';
  direction: 'inbound' | 'outbound';
  content: string | null;
  outcome: string | null;
  next_followup_date: string | null;
  created_at: string;
}

export interface Followup {
  id: string;
  customer_id: string;
  scheduled_date: string;
  completed_date: string | null;
  status: 'pending' | 'completed' | 'cancelled';
  content: string | null;
  result: string | null;
  created_at: string;
}

export interface CustomerDetail extends Customer {
  interactions: Interaction[];
  followups: Followup[];
}

export interface AnalysisResult {
  customer_profile: string;
  purchase_intent: number;
  price_sensitivity: 'low' | 'medium' | 'high';
  recommended_products: string[];
  recommended_actions: string[];
  forbidden_actions: string[];
  risk_notes: string[];
}

export interface CustomerCreate {
  name: string;
  age?: number | null;
  gender?: 'male' | 'female' | null;
  phone?: string | null;
  customer_type?: 'prospective' | 'active' | 'lapsed';
  tags?: string[] | null;
  insurance_type?: string | null;
  current_stage?: string;
  intention_level?: number;
  source_channel?: string | null;
  notes?: string | null;
  assigned_to?: string | null;
}

export type CustomerUpdate = Partial<CustomerCreate>;

export interface InteractionCreate {
  type: 'phone' | 'wechat' | 'f2f' | 'email' | 'other';
  direction: 'inbound' | 'outbound';
  content?: string | null;
  outcome?: string | null;
  next_followup_date?: string | null;
}

export interface FollowupCreate {
  scheduled_date: string;
  content?: string | null;
  status?: 'pending' | 'completed' | 'cancelled';
  result?: string | null;
}

export interface CustomerListParams {
  customer_type?: string;
  current_stage?: string;
  intention_level?: number;
  tag?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export interface CustomerListResult {
  items: Customer[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// ----------- API Functions -----------

export async function listCustomers(
  params: CustomerListParams = {},
): Promise<CustomerListResult> {
  const res = await api.get<{
    success: boolean;
    data: Customer[];
    pagination: {
      page: number;
      page_size: number;
      total: number;
      total_pages: number;
    };
  }>('/customers', { params });

  const { pagination } = res.data;
  return {
    items: res.data.data ?? [],
    total: pagination?.total ?? 0,
    page: pagination?.page ?? 1,
    pageSize: pagination?.page_size ?? 20,
    totalPages: pagination?.total_pages ?? 1,
  };
}

export async function getCustomer(id: string): Promise<CustomerDetail> {
  const res = await api.get<{ success: boolean; data: CustomerDetail }>(
    `/customers/${id}`,
  );
  return res.data.data;
}

export async function createCustomer(data: CustomerCreate): Promise<Customer> {
  const res = await api.post<{ success: boolean; data: Customer }>(
    '/customers',
    data,
  );
  return res.data.data;
}

export async function updateCustomer(
  id: string,
  data: CustomerUpdate,
): Promise<Customer> {
  const res = await api.put<{ success: boolean; data: Customer }>(
    `/customers/${id}`,
    data,
  );
  return res.data.data;
}

export async function deleteCustomer(id: string): Promise<void> {
  await api.delete(`/customers/${id}`);
}

export async function addInteraction(
  customerId: string,
  data: InteractionCreate,
): Promise<Interaction> {
  const res = await api.post<{
    success: boolean;
    data: Interaction;
  }>(`/customers/${customerId}/interactions`, data);
  return res.data.data;
}

export async function addFollowup(
  customerId: string,
  data: FollowupCreate,
): Promise<Followup> {
  const res = await api.post<{
    success: boolean;
    data: Followup;
  }>(`/customers/${customerId}/followups`, data);
  return res.data.data;
}

// ----------- SSE: AI Analysis -----------

/**
 * Stream AI analysis for a customer via SSE.
 * Yields `{ event, data }` objects for each SSE event.
 */
export async function* analyzeCustomerSSE(
  customerId: string,
): AsyncGenerator<{ event: string; data: Record<string, unknown> }> {
  const token = useAuthStore.getState().token;
  const baseUrl = '/api/v1';

  const response = await fetch(
    `${baseUrl}/customers/${customerId}/ai-analysis`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: token ? `Bearer ${token}` : '',
        Accept: 'text/event-stream',
      },
    },
  );

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('No response body');

  const decoder = new TextDecoder();
  let buffer = '';
  let currentEvent = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim();
      } else if (line.startsWith('data: ')) {
        const raw = line.slice(6);
        try {
          const parsed = JSON.parse(raw);
          const evt =
            typeof parsed.event === 'string' ? parsed.event : currentEvent || '';
          const payload =
            parsed.data !== undefined && typeof parsed.data === 'object'
              ? (parsed.data as Record<string, unknown>)
              : parsed;
          yield { event: evt, data: payload };
        } catch {
          // Non-JSON data (e.g. plain text token)
          yield {
            event: currentEvent || 'token',
            data: { token: raw },
          };
        }
        currentEvent = '';
      } else if (line === '') {
        currentEvent = '';
      }
    }
  }
}
