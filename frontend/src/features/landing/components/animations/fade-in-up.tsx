'use client';

import { ReactNode } from 'react';
import { motion } from 'framer-motion';

interface FadeInUpProps {
  children: ReactNode;
  className?: string;
  delay?: number;
  distance?: number;
}

export function FadeInUp({ children, className = '', delay = 0, distance = 50 }: FadeInUpProps) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: distance }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-100px' }}
      transition={{
        duration: 0.6,
        delay,
        ease: [0.25, 0.1, 0.25, 1],
      }}
    >
      {children}
    </motion.div>
  );
}
