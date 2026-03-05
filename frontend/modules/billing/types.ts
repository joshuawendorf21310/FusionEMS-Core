/**
 * Billing module types.
 */

export type ClaimStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'ACCEPTED'
  | 'REJECTED'
  | 'PAID'
  | 'DENIED'
  | 'APPEAL'
  | 'VOID';

export interface Claim {
  id: string;
  patientName: string;
  dateOfService: string;
  payer: string;
  totalBilled: number;
  totalPaid: number;
  balance: number;
  status: ClaimStatus;
  submittedAt: string | null;
  paidAt: string | null;
}

export interface ArAgingBucket {
  label: string;
  range: string;
  total: number;
  count: number;
}

export interface RevenueMetrics {
  mrr: number;
  mrrDelta: number;
  totalAR: number;
  totalDenials: number;
  totalClaims: number;
  collectionRate: number;
}
