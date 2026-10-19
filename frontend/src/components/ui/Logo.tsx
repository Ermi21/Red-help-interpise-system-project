import React from 'react';

interface LogoProps {
  className?: string;
  size?: number;
  variant?: 'icon' | 'full';
  showSubtitle?: boolean;
}

export default function Logo({ 
  className = '', 
  size = 28, 
  variant = 'icon',
  showSubtitle = true 
}: LogoProps) {
  if (variant === 'full') {
    return (
      <div className={`flex items-center space-x-2.5 select-none ${className}`}>
        <img 
          src="/assets/brand/logo.svg" 
          alt="Red Cloud ICT Solutions"
          className="h-8 w-auto object-contain flex-shrink-0"
          onError={(e) => {
            // If image fails, fallback to vector representation
            (e.target as HTMLElement).style.display = 'none';
          }}
        />
        <div className="flex flex-col leading-none">
          <div className="flex items-center">
            <span className="font-black text-red-600 tracking-tight text-lg">RED</span>
            <span className="font-extrabold text-textPrimary tracking-tight text-lg ml-0.5">Cloud</span>
          </div>
          {showSubtitle && (
            <span className="text-[9px] font-semibold text-textSecondary uppercase tracking-widest mt-0.5">
              ICT Solutions
            </span>
          )}
        </div>
      </div>
    );
  }

  // Icon variant - crisp vector red cloud with Ethiopian telecom/ICT vibrancy
  return (
    <svg 
      xmlns="http://www.w3.org/2000/svg" 
      width={size} 
      height={(size * 44) / 48} 
      viewBox="0 0 52 46"
      fill="none" 
      className={`filter drop-shadow-[0_2px_8px_rgba(227,6,19,0.35)] ${className}`}
      role="img"
      aria-label="Red Cloud Logo"
    >
      <defs>
        <linearGradient id="redCloudGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#FF1E28" />
          <stop offset="50%" stopColor="#E30613" />
          <stop offset="100%" stopColor="#B3000C" />
        </linearGradient>
        <linearGradient id="redCloudHighlight" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.5" />
          <stop offset="100%" stopColor="#FFFFFF" stopOpacity="0.0" />
        </linearGradient>
      </defs>

      {/* Main Cloud Silhouette */}
      <g>
        <ellipse cx="26" cy="27" rx="22" ry="13" fill="url(#redCloudGrad)"/>
        <circle cx="15" cy="24" r="10.5" fill="url(#redCloudGrad)"/>
        <circle cx="28" cy="17" r="13.5" fill="url(#redCloudGrad)"/>
        <circle cx="39" cy="24" r="9.5" fill="url(#redCloudGrad)"/>
        
        {/* Modern cyber highlight arc */}
        <ellipse cx="25" cy="15" rx="7.5" ry="4.5" fill="url(#redCloudHighlight)"/>
      </g>
    </svg>
  );
}
