import type { User } from '@supabase/supabase-js';

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  avatarUrl: string | null;
  createdAt: string | null;
  lastLoginAt: string | null;
}

function readMetadataValue(user: User, keys: string[]): string | undefined {
  const metadata = (user.user_metadata ?? {}) as Record<string, unknown>;

  for (const key of keys) {
    const value = metadata[key];
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return undefined;
}

function resolveProfileName(user: User): string {
  return (
    readMetadataValue(user, ['full_name', 'name', 'display_name']) ??
    user.email?.split('@')[0] ??
    'StrategAI User'
  );
}

export function buildUserProfile(user: User | null): UserProfile | null {
  if (!user) {
    return null;
  }

  const avatarUrl = readMetadataValue(user, ['avatar_url', 'picture']) ?? null;

  return {
    id: user.id,
    name: resolveProfileName(user),
    email: user.email ?? '',
    avatarUrl,
    createdAt: user.created_at ?? null,
    lastLoginAt: user.last_sign_in_at ?? null,
  };
}

export function formatAuthError(error: unknown, fallback = 'Something went wrong. Please try again.') {
  if (!error) {
    return fallback;
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  if (typeof error === 'string' && error.trim()) {
    return error;
  }

  if (typeof error === 'object' && error !== null && 'message' in error) {
    const message = String((error as { message?: unknown }).message ?? '').trim();
    if (message) {
      return message;
    }
  }

  return fallback;
}

