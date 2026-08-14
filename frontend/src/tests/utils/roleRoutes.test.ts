import { describe, it, expect } from 'vitest';
import { hasRouteAccess, ROLE_ACCESS } from '../../config/roleRoutes';

describe('hasRouteAccess', () => {
  it('SYSTEM_ADMIN can access all admin pages', () => {
    expect(hasRouteAccess('/admin/users', 'SYSTEM_ADMIN')).toBe(true);
    expect(hasRouteAccess('/admin/analytics', 'SYSTEM_ADMIN')).toBe(true);
    expect(hasRouteAccess('/admin/audit-logs', 'SYSTEM_ADMIN')).toBe(true);
    expect(hasRouteAccess('/admin/audit', 'SYSTEM_ADMIN')).toBe(true);
    expect(hasRouteAccess('/admin/compliance', 'SYSTEM_ADMIN')).toBe(true);
    expect(hasRouteAccess('/admin/settings', 'SYSTEM_ADMIN')).toBe(true);
  });

  it('AGENT cannot access admin pages', () => {
    expect(hasRouteAccess('/admin/users', 'AGENT')).toBe(false);
    expect(hasRouteAccess('/admin/analytics', 'AGENT')).toBe(false);
    expect(hasRouteAccess('/admin/settings', 'AGENT')).toBe(false);
  });

  it('all roles can access /dashboard', () => {
    const roles = ['SYSTEM_ADMIN', 'HQ_ADMIN', 'BRANCH_ADMIN', 'TEAM_LEADER', 'COMPLIANCE', 'KNOWLEDGE_ADMIN', 'AGENT'];
    for (const role of roles) {
      expect(hasRouteAccess('/dashboard', role)).toBe(true);
    }
  });

  it('all roles can access /product-qa', () => {
    const roles = ['SYSTEM_ADMIN', 'HQ_ADMIN', 'BRANCH_ADMIN', 'TEAM_LEADER', 'COMPLIANCE', 'KNOWLEDGE_ADMIN', 'AGENT'];
    for (const role of roles) {
      expect(hasRouteAccess('/product-qa', role)).toBe(true);
    }
  });

  it('COMPLIANCE role can access /admin/compliance', () => {
    expect(hasRouteAccess('/admin/compliance', 'COMPLIANCE')).toBe(true);
  });

  it('COMPLIANCE role cannot access other admin pages', () => {
    expect(hasRouteAccess('/admin/users', 'COMPLIANCE')).toBe(false);
    expect(hasRouteAccess('/admin/settings', 'COMPLIANCE')).toBe(false);
  });

  it('unknown path returns true by default', () => {
    expect(hasRouteAccess('/some/random/path', 'AGENT')).toBe(true);
    expect(hasRouteAccess('/unknown', 'SYSTEM_ADMIN')).toBe(true);
  });

  it('prefix matching works for /admin/*', () => {
    // /admin/users/new should match /admin/users prefix
    expect(hasRouteAccess('/admin/users/new', 'SYSTEM_ADMIN')).toBe(true);
    expect(hasRouteAccess('/admin/users/new', 'AGENT')).toBe(false);

    // /admin/analytics/detail should match /admin/analytics prefix
    expect(hasRouteAccess('/admin/analytics/detail', 'HQ_ADMIN')).toBe(true);
    expect(hasRouteAccess('/admin/analytics/detail', 'AGENT')).toBe(false);
  });

  it('KNOWLEDGE_ADMIN can access /knowledge', () => {
    expect(hasRouteAccess('/knowledge', 'KNOWLEDGE_ADMIN')).toBe(true);
  });

  it('TEAM_LEADER cannot access /knowledge', () => {
    // TEAM_LEADER is not in the /knowledge access list
    expect(hasRouteAccess('/knowledge', 'TEAM_LEADER')).toBe(false);
  });

  it('BRANCH_ADMIN cannot access /admin/settings (SYSTEM_ADMIN only)', () => {
    expect(hasRouteAccess('/admin/settings', 'BRANCH_ADMIN')).toBe(false);
  });

  it('ROLE_ACCESS contains expected keys', () => {
    expect(ROLE_ACCESS).toHaveProperty('/dashboard');
    expect(ROLE_ACCESS).toHaveProperty('/product-qa');
    expect(ROLE_ACCESS).toHaveProperty('/admin/users');
    expect(ROLE_ACCESS).toHaveProperty('/admin/settings');
  });

  it('longest prefix match is preferred', () => {
    // /admin/audit-logs/something should match /admin/audit-logs (longer) not /admin/audit
    expect(hasRouteAccess('/admin/audit-logs/123', 'SYSTEM_ADMIN')).toBe(true);
  });
});
