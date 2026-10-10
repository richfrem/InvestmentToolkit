import type { ReactElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';
import { ErrorBoundary } from './ErrorBoundary';

describe('ErrorBoundary', () => {
    it('passes the children through when nothing has failed', () => {
        const boundary = new ErrorBoundary({ children: 'all good' });
        expect(boundary.render()).toBe('all good');
    });

    it('turns a caught error into state', () => {
        expect(ErrorBoundary.getDerivedStateFromError(new Error('kaboom')).error?.message).toBe('kaboom');
    });

    it('renders a message that names the error and offers a reload, instead of nothing', () => {
        const boundary = new ErrorBoundary({ children: 'child' });
        boundary.state = ErrorBoundary.getDerivedStateFromError(new Error('kaboom in a child'));
        const html = renderToStaticMarkup(boundary.render() as ReactElement);
        expect(html).toContain('Something went wrong on this screen');
        expect(html).toContain('kaboom in a child');
        expect(html).toContain('Reload');
        expect(html).toContain('restart the backend');
        expect(html).toContain('role="alert"');
    });
});
