export enum LeadStatus {
  New = "new",
  Qualifying = "qualifying",
  Qualified = "qualified",
  Assigned = "assigned",
  InProgress = "in_progress",
  AppointmentBooked = "appointment_booked",
  Stale = "stale",
  Escalated = "escalated",
  Closed = "closed",
  Spam = "spam",
}

export enum MessageStatus {
  Queued = "queued",
  Sent = "sent",
  Delivered = "delivered",
  Failed = "failed",
  Undelivered = "undelivered",
  Read = "read",
}

export enum SyncStatus {
  Pending = "pending",
  Success = "success",
  Failed = "failed",
  Retrying = "retrying",
}
