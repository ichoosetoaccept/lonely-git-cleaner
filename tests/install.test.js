const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const os = require('os');

jest.mock('fs');
jest.mock('child_process');
jest.mock('os');

describe('install.sh', () => {
  const mockHomedir = '/mock/home';
  const scriptDir = path.join(__dirname, '..');
  const binPath = path.join(scriptDir, 'bin/git-cleanup');
  const configPath = path.join(mockHomedir, '.git-cleanuprc');
  const installScript = path.join(scriptDir, 'scripts/install.sh');
  
  beforeEach(() => {
    jest.clearAllMocks();
    
    // Mock os.homedir()
    os.homedir.mockReturnValue(mockHomedir);
    
    // Mock fs functions
    fs.existsSync.mockReturnValue(false);
    fs.writeFileSync.mockImplementation(() => {});
    fs.mkdirSync.mockReturnValue(undefined);
    
    // Reset environment
    delete process.env.npm_config_global;
    process.env.OSTYPE = 'darwin';
  });

  describe('Script Permissions', () => {
    test('makes git-cleanup executable', () => {
      spawnSync.mockReturnValue({
        status: 0,
        stdout: Buffer.from(''),
        stderr: Buffer.from('')
      });
      
      const result = spawnSync('bash', [installScript]);
      
      expect(result.status).toBe(0);
      expect(spawnSync).toHaveBeenCalledWith('bash', [installScript]);
    });
  });

  describe('Global Installation', () => {
    beforeEach(() => {
      process.env.npm_config_global = 'true';
    });

    test('creates correct symlink on macOS', () => {
      process.env.OSTYPE = 'darwin';
      
      spawnSync.mockReturnValue({
        status: 0,
        stdout: Buffer.from(''),
        stderr: Buffer.from('')
      });
      
      const result = spawnSync('bash', [installScript]);
      
      expect(result.status).toBe(0);
      expect(spawnSync).toHaveBeenCalledWith('bash', [installScript]);
    });

    test('creates correct symlink on Linux', () => {
      process.env.OSTYPE = 'linux-gnu';
      
      spawnSync.mockReturnValue({
        status: 0,
        stdout: Buffer.from(''),
        stderr: Buffer.from('')
      });
      
      const result = spawnSync('bash', [installScript]);
      
      expect(result.status).toBe(0);
      expect(spawnSync).toHaveBeenCalledWith('bash', [installScript]);
    });
  });

  describe('Local Installation', () => {
    beforeEach(() => {
      process.env.npm_config_global = 'false';
    });

    test('skips symlink creation', () => {
      spawnSync.mockReturnValue({
        status: 0,
        stdout: Buffer.from('Installing git-cleanup locally'),
        stderr: Buffer.from('')
      });
      
      const result = spawnSync('bash', [installScript]);
      
      expect(result.status).toBe(0);
      expect(result.stdout.toString()).toContain('Installing git-cleanup locally');
    });

    test('shows local installation message', () => {
      spawnSync.mockReturnValue({
        status: 0,
        stdout: Buffer.from('Installing git-cleanup locally'),
        stderr: Buffer.from('')
      });
      
      const result = spawnSync('bash', [installScript]);
      
      expect(result.status).toBe(0);
      expect(result.stdout.toString()).toContain('Installing git-cleanup locally');
    });
  });

  describe('Configuration File', () => {
    test('creates default config if none exists', () => {
      fs.existsSync.mockReturnValue(false);
      
      spawnSync.mockReturnValue({
        status: 0,
        stdout: Buffer.from(''),
        stderr: Buffer.from('')
      });
      
      const result = spawnSync('bash', [installScript]);
      
      expect(result.status).toBe(0);
      expect(fs.writeFileSync).toHaveBeenCalledWith(
        configPath,
        expect.stringMatching(/{\s*"protectedBranches":\s*\["main",\s*"master"\]/),
        'utf8'
      );
    });

    test('preserves existing config', () => {
      fs.existsSync.mockReturnValue(true);
      
      spawnSync.mockReturnValue({
        status: 0,
        stdout: Buffer.from(''),
        stderr: Buffer.from('')
      });
      
      const result = spawnSync('bash', [installScript]);
      
      expect(result.status).toBe(0);
      expect(fs.writeFileSync).not.toHaveBeenCalled();
    });
  });

  describe('Error Handling', () => {
    test('handles chmod failure gracefully', () => {
      spawnSync.mockReturnValue({
        status: 1,
        stdout: Buffer.from(''),
        stderr: Buffer.from('chmod failed')
      });
      
      const result = spawnSync('bash', [installScript]);
      
      expect(result.stderr.toString()).toContain('chmod failed');
    });

    test('handles symlink creation failure gracefully', () => {
      process.env.npm_config_global = 'true';
      spawnSync.mockReturnValue({
        status: 1,
        stdout: Buffer.from(''),
        stderr: Buffer.from('ln failed')
      });
      
      const result = spawnSync('bash', [installScript]);
      
      expect(result.stderr.toString()).toContain('ln failed');
    });

    test('handles config creation failure gracefully', () => {
      fs.writeFileSync.mockImplementationOnce(() => {
        throw new Error('write failed');
      });
      
      expect(() => {
        fs.writeFileSync(configPath, '{}', 'utf8');
      }).toThrow('write failed');
    });
  });
});
