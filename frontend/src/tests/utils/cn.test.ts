import { describe, it, expect } from 'vitest';
import { cn } from '../../utils/cn';

describe('cn utility', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar', 'baz')).toBe('foo bar baz');
  });

  it('handles conditional classes with boolean', () => {
    expect(cn('base', true && 'active', false && 'hidden')).toBe('base active');
  });

  it('removes undefined and null', () => {
    expect(cn('foo', undefined, null, 'bar')).toBe('foo bar');
  });

  it('handles empty input', () => {
    expect(cn()).toBe('');
  });

  it('removes empty strings', () => {
    expect(cn('foo', '', 'bar')).toBe('foo bar');
  });

  it('returns single class when only one provided', () => {
    expect(cn('solo')).toBe('solo');
  });

  it('handles all falsy values', () => {
    expect(cn(undefined, null, false, '', 0 as any)).toBe('');
  });
});
