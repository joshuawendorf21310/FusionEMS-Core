/**
 * Scheduling module types.
 */

export interface Shift {
  id: string;
  crewMemberId: string;
  crewMemberName: string;
  start: string;
  end: string;
  station: string;
  role: string;
}

export interface ScheduleDay {
  date: string;
  shifts: Shift[];
}
