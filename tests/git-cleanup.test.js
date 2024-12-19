const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const inquirer = require('inquirer');
const chalk = require('chalk');

// Mock modules
jest.mock('fs');
jest.mock('child_process');
jest.mock('inquirer');
jest.mock('chalk', () => ({
  blue: jest.fn(text => text),
  yellow: jest.fn(text => text),
  green: jest.fn(text => text),
  red: jest.fn(text => text)
}));

describe('git-cleanup', () => {
  let main;
  let mockConsoleLog;
  let mockConsoleError;
  let mockConsoleWarn;
  let mockExit;
  
  beforeEach(() => {
    // Clear all mocks and module cache
    jest.clearAllMocks();
    jest.resetModules();
    
    // Reset process.argv
    process.argv = ['node', 'git-cleanup'];
    
    // Reset fs mock implementation
    fs.existsSync.mockReturnValue(true);
    fs.readFileSync.mockReturnValue(JSON.stringify({
      protectedBranches: ['main', 'master'],
      dryRunByDefault: false,
      interactive: false,
      skipGc: false,
      reflogExpiry: '90.days'
    }));
    
    // Reset execSync mock implementation for git commands
    execSync.mockImplementation((cmd, opts = {}) => {
      if (cmd === 'git rev-parse --is-inside-work-tree') return '';
      if (cmd === 'git branch -vv') return '';
      if (cmd === 'git branch --merged') return '';
      if (cmd === 'git gc') return '';
      if (cmd === 'git prune') return '';
      if (cmd === 'git fetch -p') return '';
      if (cmd === 'rm -f .git/gc.log') return '';
      return '';
    });
    
    // Reset inquirer mock implementation
    inquirer.prompt.mockResolvedValue({ confirm: true });
    
    // Mock console methods
    mockConsoleLog = jest.spyOn(console, 'log').mockImplementation(() => {});
    mockConsoleError = jest.spyOn(console, 'error').mockImplementation(() => {});
    mockConsoleWarn = jest.spyOn(console, 'warn').mockImplementation(() => {});
    mockExit = jest.spyOn(process, 'exit').mockImplementation(() => {});
    
    // Import the module
    const module = require('../bin/git-cleanup');
    main = module.main;
  });

  describe('Configuration', () => {
    test('loads default config when no config file exists', async () => {
      fs.existsSync.mockReturnValue(false);
      
      await main();
      
      expect(mockConsoleWarn).toHaveBeenCalledWith(expect.any(String));
    });

    test('merges user config with defaults', async () => {
      const customConfig = {
        protectedBranches: ['develop'],
        dryRunByDefault: true
      };
      fs.readFileSync.mockReturnValue(JSON.stringify(customConfig));
      
      await main();
      
      expect(fs.readFileSync).toHaveBeenCalledWith(
        expect.stringContaining('.git-cleanuprc'),
        'utf8'
      );
    });

    test('handles invalid config file', async () => {
      fs.readFileSync.mockReturnValue('invalid json');
      
      await main();
      
      expect(mockConsoleWarn).toHaveBeenCalledWith(expect.any(String));
    });
  });

  describe('Git Repository Detection', () => {
    test('exits if not in a git repository', async () => {
      execSync.mockImplementationOnce(() => {
        throw new Error('not a git repository');
      });
      
      await main();
      
      expect(mockExit).toHaveBeenCalledWith(1);
      expect(mockConsoleError).toHaveBeenCalledWith(expect.any(String));
    });

    test('proceeds if in a git repository', async () => {
      await main();
      
      expect(mockExit).not.toHaveBeenCalled();
    });
  });

  describe('Branch Cleanup', () => {
    test('identifies and handles gone branches', async () => {
      execSync.mockImplementation((cmd) => {
        if (cmd === 'git branch -vv') {
          return `
            feature/123 abcd123 [origin/feature/123: gone]
            develop    efgh456 [origin/develop]
          `;
        }
        return '';
      });
      
      await main();
      
      const calls = mockConsoleLog.mock.calls.map(call => call[0]);
      expect(calls).toContain('Found 1 branches with gone remotes:');
    });

    test('identifies and handles merged branches', async () => {
      execSync.mockImplementation((cmd) => {
        if (cmd === 'git branch --merged') {
          return `
            feature/456
            hotfix/789
            * master
          `;
        }
        return '';
      });
      
      await main();
      
      const calls = mockConsoleLog.mock.calls.map(call => call[0]);
      expect(calls).toContain('Found 2 merged branches:');
    });

    test('respects protected branches', async () => {
      execSync.mockImplementation((cmd) => {
        if (cmd === 'git branch -vv') {
          return `
            main abcd123 [origin/main: gone]
            feature/123 efgh456 [origin/feature/123: gone]
          `;
        }
        return '';
      });
      
      await main();
      
      const calls = mockConsoleLog.mock.calls.map(call => call[0]);
      expect(calls).toContain('Found 1 branches with gone remotes:');
    });
  });

  describe('Interactive Mode', () => {
    beforeEach(() => {
      process.argv.push('--interactive');
    });

    test('prompts for confirmation in interactive mode', async () => {
      execSync.mockImplementation((cmd) => {
        if (cmd === 'git branch -vv') {
          return 'feature/123 abcd123 [origin/feature/123: gone]';
        }
        return '';
      });
      
      inquirer.prompt.mockResolvedValueOnce({ confirm: false });
      
      await main();
      
      expect(inquirer.prompt).toHaveBeenCalledWith([{
        type: 'confirm',
        name: 'confirm',
        message: 'Delete branch feature/123?',
        default: false
      }]);
    });

    test('skips deletion when confirmation is denied', async () => {
      execSync.mockImplementation((cmd) => {
        if (cmd === 'git branch -vv') {
          return 'feature/123 abcd123 [origin/feature/123: gone]';
        }
        return '';
      });
      
      inquirer.prompt.mockResolvedValueOnce({ confirm: false });
      
      await main();
      
      expect(execSync).not.toHaveBeenCalledWith(
        'git branch -D feature/123',
        expect.any(Object)
      );
    });
  });

  describe('Dry Run Mode', () => {
    beforeEach(() => {
      process.argv.push('--dry-run');
    });

    test('shows what would be deleted without making changes', async () => {
      execSync.mockImplementation((cmd) => {
        if (cmd === 'git branch -vv') {
          return 'feature/123 abcd123 [origin/feature/123: gone]';
        }
        return '';
      });
      
      await main();
      
      const calls = mockConsoleLog.mock.calls.map(call => call[0]);
      expect(calls).toContain('DRY RUN: No changes will be made');
      expect(execSync).not.toHaveBeenCalledWith(
        'git branch -D feature/123',
        expect.any(Object)
      );
    });
  });

  describe('Repository Optimization', () => {
    test('runs gc and prune when enabled', async () => {
      await main();
      
      expect(execSync).toHaveBeenCalledWith(
        'git gc',
        { encoding: 'utf8', stdio: 'inherit' }
      );
      expect(execSync).toHaveBeenCalledWith(
        'git prune',
        { encoding: 'utf8', stdio: 'inherit' }
      );
    });

    test('skips gc when --no-gc flag is used', async () => {
      process.argv.push('--no-gc');
      
      await main();
      
      expect(execSync).not.toHaveBeenCalledWith(
        'git gc',
        expect.any(Object)
      );
      expect(execSync).not.toHaveBeenCalledWith(
        'git prune',
        expect.any(Object)
      );
    });
  });
});
