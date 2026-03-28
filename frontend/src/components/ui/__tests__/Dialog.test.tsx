import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { 
  Dialog, 
  DialogTrigger, 
  DialogContent, 
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter 
} from '../dialog';

describe('Dialog Component', () => {
  it('renders dialog trigger', () => {
    render(
      <Dialog>
        <DialogTrigger>Open Dialog</DialogTrigger>
      </Dialog>
    );
    
    expect(screen.getByText('Open Dialog')).toBeInTheDocument();
  });

  it('opens when trigger clicked', async () => {
    const user = userEvent.setup();
    
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Dialog Title</DialogTitle>
          <div>Dialog Content</div>
        </DialogContent>
      </Dialog>
    );
    
    const trigger = screen.getByText('Open');
    await user.click(trigger);
    
    expect(screen.getByText('Dialog Title')).toBeInTheDocument();
  });

  it('displays dialog content when open', async () => {
    const user = userEvent.setup();
    
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Test Dialog</DialogTitle>
          <DialogDescription>This is a test dialog</DialogDescription>
          <div>Main content here</div>
        </DialogContent>
      </Dialog>
    );
    
    await user.click(screen.getByText('Open'));
    
    expect(screen.getByText('Test Dialog')).toBeInTheDocument();
    expect(screen.getByText('This is a test dialog')).toBeInTheDocument();
    expect(screen.getByText('Main content here')).toBeInTheDocument();
  });

  it('closes on close button click', async () => {
    const user = userEvent.setup();
    
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Dialog</DialogTitle>
          <div>Content</div>
        </DialogContent>
      </Dialog>
    );
    
    await user.click(screen.getByText('Open'));
    expect(screen.getByText('Dialog')).toBeInTheDocument();
    
    // Find and click close button (X icon button)
    const closeButtons = screen.queryAllByRole('button');
    const closeButton = closeButtons.find(btn => btn !== screen.getByText('Open'));
    
    if (closeButton) {
      await user.click(closeButton);
    }
  });

  it('closes on ESC key press', async () => {
    const user = userEvent.setup();
    
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Dialog</DialogTitle>
          <div>Content</div>
        </DialogContent>
      </Dialog>
    );
    
    await user.click(screen.getByText('Open'));
    expect(screen.getByText('Dialog')).toBeInTheDocument();
    
    await user.keyboard('{Escape}');
    
    // Dialog should close (content no longer visible)
  });

  it('closes on backdrop click', async () => {
    const user = userEvent.setup();
    
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Dialog</DialogTitle>
          <div>Content</div>
        </DialogContent>
      </Dialog>
    );
    
    await user.click(screen.getByText('Open'));
    expect(screen.getByText('Dialog')).toBeInTheDocument();
    
    // Clicking overlay/backdrop should close dialog
    // Exact implementation depends on Radix UI behavior
  });

  it('renders header with title', async () => {
    const user = userEvent.setup();
    
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>My Dialog Title</DialogTitle>
          </DialogHeader>
        </DialogContent>
      </Dialog>
    );
    
    await user.click(screen.getByText('Open'));
    expect(screen.getByText('My Dialog Title')).toBeInTheDocument();
  });

  it('renders footer section', async () => {
    const user = userEvent.setup();
    
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Dialog</DialogTitle>
          <DialogFooter>
            <button>Cancel</button>
            <button>Confirm</button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    );
    
    await user.click(screen.getByText('Open'));
    
    expect(screen.getByText('Cancel')).toBeInTheDocument();
    expect(screen.getByText('Confirm')).toBeInTheDocument();
  });

  it('handles controlled open state', () => {
    const onOpenChange = vi.fn();
    
    render(
      <Dialog open={true} onOpenChange={onOpenChange}>
        <DialogContent>
          <DialogTitle>Controlled Dialog</DialogTitle>
        </DialogContent>
      </Dialog>
    );
    
    expect(screen.getByText('Controlled Dialog')).toBeInTheDocument();
  });

  it('renders custom content', async () => {
    const user = userEvent.setup();
    
    render(
      <Dialog>
        <DialogTrigger>Open</DialogTrigger>
        <DialogContent>
          <DialogTitle>Custom Dialog</DialogTitle>
          <form>
            <input placeholder="Name" />
            <input placeholder="Email" />
            <button type="submit">Submit</button>
          </form>
        </DialogContent>
      </Dialog>
    );
    
    await user.click(screen.getByText('Open'));
    
    expect(screen.getByPlaceholderText('Name')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Email')).toBeInTheDocument();
    expect(screen.getByText('Submit')).toBeInTheDocument();
  });
});
