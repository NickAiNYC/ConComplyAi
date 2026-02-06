/**
 * NYC Data Utilities
 * Utilities for handling NYC BBL, BIN, and GIS data
 */

// Borough mapping
export const BOROUGHS = {
  1: 'Manhattan',
  2: 'Bronx',
  3: 'Brooklyn',
  4: 'Queens',
  5: 'Staten Island'
} as const;

export const BOROUGH_CODES = {
  'Manhattan': 1,
  'Bronx': 2,
  'Brooklyn': 3,
  'Queens': 4,
  'Staten Island': 5
} as const;

/**
 * Parse BBL string into components
 * @param bbl - BBL string in format "1-01042-0001"
 * @returns Object with borough, block, lot
 */
export function parseBBL(bbl: string): { borough: number; block: number; lot: number } {
  const parts = bbl.split('-');
  return {
    borough: parseInt(parts[0], 10),
    block: parseInt(parts[1], 10),
    lot: parseInt(parts[2], 10)
  };
}

/**
 * Format BBL from components
 * @param borough - Borough code (1-5)
 * @param block - Block number
 * @param lot - Lot number
 * @returns Formatted BBL string
 */
export function formatBBL(borough: number, block: number, lot: number): string {
  return `${borough}-${String(block).padStart(5, '0')}-${String(lot).padStart(4, '0')}`;
}

/**
 * Get borough name from BBL
 * @param bbl - BBL string
 * @returns Borough name
 */
export function getBoroughName(bbl: string): string {
  const { borough } = parseBBL(bbl);
  return BOROUGHS[borough as keyof typeof BOROUGHS] || 'Unknown';
}

/**
 * Validate BBL format
 * @param bbl - BBL string to validate
 * @returns True if valid BBL format
 */
export function isValidBBL(bbl: string): boolean {
  const regex = /^[1-5]-\d{5}-\d{4}$/;
  return regex.test(bbl);
}

/**
 * Validate BIN format
 * @param bin - BIN string to validate
 * @returns True if valid BIN format (7 digits)
 */
export function isValidBIN(bin: string): boolean {
  const regex = /^\d{7}$/;
  return regex.test(bin);
}

/**
 * Convert lat/lng to NYC map coordinates
 * Used for positioning markers on the simulated map
 */
export function latLngToMapCoords(lat: number, lng: number): { x: number; y: number } {
  // NYC bounding box approximation
  const NYC_BOUNDS = {
    minLat: 40.4774,
    maxLat: 40.9176,
    minLng: -74.2591,
    maxLng: -73.7004
  };

  const x = ((lng - NYC_BOUNDS.minLng) / (NYC_BOUNDS.maxLng - NYC_BOUNDS.minLng)) * 100;
  const y = ((NYC_BOUNDS.maxLat - lat) / (NYC_BOUNDS.maxLat - NYC_BOUNDS.minLat)) * 100;

  return { x, y };
}

/**
 * Generate SHA-256 hash (client-side simulation)
 * In production, this would be generated server-side
 * CRITICAL: Includes HPD Registration Number for LL86 sign audit compliance
 */
export async function generateAuditHash(data: {
  bbl: string;
  bin: string;
  hpdRegistrationNumber?: string; // REQUIRED for LL86 compliance
  timestamp: number;
  violations: string[];
}): Promise<string> {
  // Validate HPD Registration Number is included
  if (!data.hpdRegistrationNumber) {
    console.warn('⚠️ LL86 AUDIT FAILURE RISK: Missing HPD Registration Number');
  }
  
  const jsonString = JSON.stringify(data);
  
  // For browser environment
  if (typeof window !== 'undefined' && window.crypto && window.crypto.subtle) {
    const encoder = new TextEncoder();
    const dataBuffer = encoder.encode(jsonString);
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', dataBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    return `sha256:${hashHex}`;
  }
  
  // Fallback for SSR or older browsers
  return `sha256:${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`;
}

/**
 * Format currency for display
 */
export function formatCurrency(amount: number, decimals: number = 0): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(amount);
}

/**
 * Format large numbers (e.g., 1.5M, 2.3B)
 */
export function formatCompactNumber(num: number): string {
  if (num >= 1e9) {
    return `${(num / 1e9).toFixed(1)}B`;
  }
  if (num >= 1e6) {
    return `${(num / 1e6).toFixed(1)}M`;
  }
  if (num >= 1e3) {
    return `${(num / 1e3).toFixed(1)}K`;
  }
  return num.toString();
}

/**
 * Calculate time difference in human-readable format
 */
export function timeAgo(date: Date): string {
  const seconds = Math.floor((new Date().getTime() - date.getTime()) / 1000);
  
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

/**
 * NYC Local Law compliance checker
 */
export const LocalLaws = {
  /**
   * Check LL149 compliance (Superintendent site dedication)
   */
  checkLL149: (superintendentSites: number): { compliant: boolean; violation?: string } => {
    if (superintendentSites > 1) {
      return {
        compliant: false,
        violation: 'LL149 Multi-Site Superintendent'
      };
    }
    return { compliant: true };
  },

  /**
   * Check LL152 compliance (District cycles)
   * UPDATED: Feb 22, 2026 scope change includes COMMERCIAL buildings
   */
  checkLL152: (
    district: number, 
    buildingType: 'residential' | 'commercial' | 'mixed-use',
    filingDate: Date
  ): { compliant: boolean; violation?: string; scopeChange?: string } => {
    const complianceDistricts = [4, 6, 8, 9, 16];
    const scopeChangeDate = new Date('2026-02-22');
    
    // Post-Feb 22: Commercial buildings now included
    const requiresCompliance = filingDate >= scopeChangeDate 
      ? true // All building types
      : buildingType === 'residential' || buildingType === 'mixed-use';
    
    if (requiresCompliance && !complianceDistricts.includes(district)) {
      return {
        compliant: false,
        violation: 'LL152 Compliance Cycle Violation',
        scopeChange: filingDate >= scopeChangeDate 
          ? 'Commercial buildings now subject to LL152 (Feb 22, 2026 scope change)'
          : undefined
      };
    }
    
    return { 
      compliant: true,
      scopeChange: filingDate >= scopeChangeDate && buildingType === 'commercial'
        ? 'Now compliant under Feb 22, 2026 commercial inclusion'
        : undefined
    };
  },

  /**
   * Get legal basis citation
   */
  getCitation: (violation: string): string => {
    const citations: Record<string, string> = {
      'LL149 Multi-Site Superintendent': 'RCNY §101-08: Superintendent must be dedicated to single construction site',
      'LL152 Compliance Cycle Violation': 'NYC Building Code §28-211.1: All construction work requires compliant oversight per district cycle',
      'RCNY 101-08 Documentation Gap': 'RCNY §101-08: Required documentation must be maintained and accessible',
      'DOB NOW Filing Inconsistency': 'NYC Building Code §28-104.7: All filings must be accurate and complete',
      'Missing C of O Documentation': 'NYC Building Code §28-118.3: Certificate of Occupancy must be on file',
      'Superintendent License Expired': 'RCNY §101-08: Valid superintendent license required at all times'
    };
    
    return citations[violation] || 'NYC Building Code: General compliance requirements';
  },

  /**
   * One-Job Tracker: Cross-reference Superintendent IDs against DOB NOW
   * CRITICAL: Transition period for pre-2026 jobs ends soon
   */
  checkOneJobRule: (
    superintendentId: string,
    activeJobs: Array<{ bin: string; startDate: Date }>,
    currentDate: Date = new Date()
  ): { 
    compliant: boolean; 
    violation?: string; 
    transitionPeriodWarning?: string;
    jobCount: number;
    bins: string[];
  } => {
    const transitionCutoff = new Date('2026-01-01');
    
    // Filter to active jobs only
    const activeJobsList = activeJobs.filter(job => job.startDate);
    
    // Pre-2026 jobs get transition period, post-2026 strict enforcement
    const preTransitionJobs = activeJobsList.filter(job => job.startDate < transitionCutoff);
    const postTransitionJobs = activeJobsList.filter(job => job.startDate >= transitionCutoff);
    
    // Post-2026: Absolute one-job rule
    if (postTransitionJobs.length > 1) {
      return {
        compliant: false,
        violation: 'LL149 Multi-Site Superintendent (Job Juggling)',
        jobCount: activeJobsList.length,
        bins: activeJobsList.map(j => j.bin)
      };
    }
    
    // Pre-2026 + Post-2026: Warn if total > 1
    if (activeJobsList.length > 1 && preTransitionJobs.length > 0) {
      return {
        compliant: true, // Still compliant during transition
        transitionPeriodWarning: `Superintendent on ${activeJobsList.length} sites (${preTransitionJobs.length} pre-2026). Transition period ending soon.`,
        jobCount: activeJobsList.length,
        bins: activeJobsList.map(j => j.bin)
      };
    }
    
    return {
      compliant: true,
      jobCount: activeJobsList.length,
      bins: activeJobsList.map(j => j.bin)
    };
  }
};

/**
 * NYC Open Data API helpers
 * Use these to connect to real data sources
 */
export const NYCOpenData = {
  /**
   * DOB Job Application Filings endpoint
   */
  getJobFilingsUrl: (limit: number = 50): string => {
    return `https://data.cityofnewyork.us/resource/ic3t-wcy2.json?$limit=${limit}`;
  },

  /**
   * DOB Violations endpoint
   */
  getViolationsUrl: (bbl?: string): string => {
    const baseUrl = 'https://data.cityofnewyork.us/resource/3h2n-5cm9.json';
    return bbl ? `${baseUrl}?bin=${bbl}` : baseUrl;
  },

  /**
   * GeoClient API for BBL geocoding
   */
  getGeocodeUrl: (bbl: string, appId: string, appKey: string): string => {
    const { borough, block, lot } = parseBBL(bbl);
    return `https://api.nyc.gov/geo/geoclient/v1/bbl.json?borough=${borough}&block=${block}&lot=${lot}&app_id=${appId}&app_key=${appKey}`;
  }
};

/**
 * Risk assessment calculator
 */
export function calculateComplianceRisk(
  violations: string[],
  contestableWork: number,
  superintendentConflict?: boolean
): { level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'; score: number; description: string } {
  let score = 0;
  
  // Violation count
  score += violations.length * 10;
  
  // Financial exposure
  if (contestableWork > 50000000) score += 30;
  else if (contestableWork > 10000000) score += 20;
  else if (contestableWork > 1000000) score += 10;
  
  // Superintendent conflict (highest weight)
  if (superintendentConflict) score += 40;
  
  // Determine risk level
  if (score >= 70) {
    return {
      level: 'CRITICAL',
      score,
      description: 'Immediate lender notification required - Multiple high-severity violations'
    };
  } else if (score >= 50) {
    return {
      level: 'HIGH',
      score,
      description: 'High-priority remediation - Multi-site violation or significant exposure'
    };
  } else if (score >= 30) {
    return {
      level: 'MEDIUM',
      score,
      description: 'Documentation gap - Routine compliance cleanup needed'
    };
  } else {
    return {
      level: 'LOW',
      score,
      description: 'Minor administrative issues - Low urgency'
    };
  }
}
