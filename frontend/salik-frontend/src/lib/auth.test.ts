import assert from 'node:assert/strict';
import type { User } from '@supabase/supabase-js';
import { buildUserProfile } from './auth';

const googleUser = {
  id: 'user-123',
  email: 'ayesha@example.com',
  created_at: '2026-07-12T08:30:00.000Z',
  last_sign_in_at: '2026-07-12T10:15:00.000Z',
  user_metadata: {
    full_name: 'Ayesha Iftikhar',
    avatar_url: 'https://example.com/avatar.png',
  },
} as unknown as User;

const profile = buildUserProfile(googleUser);

assert.equal(profile?.id, 'user-123');
assert.equal(profile?.name, 'Ayesha Iftikhar');
assert.equal(profile?.email, 'ayesha@example.com');
assert.equal(profile?.avatarUrl, 'https://example.com/avatar.png');
assert.equal(profile?.createdAt, '2026-07-12T08:30:00.000Z');
assert.equal(profile?.lastLoginAt, '2026-07-12T10:15:00.000Z');


