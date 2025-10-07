'use client';

import { motion } from 'framer-motion';

interface RevealTextProps {
  text: string;
  className?: string;
  delay?: number;
  duration?: number;
}

export function RevealText({ text, className = '', delay = 0, duration = 0.8 }: RevealTextProps) {
  const words = text.split(' ');

  return (
    <motion.div
      className={className}
      initial='hidden'
      whileInView='visible'
      viewport={{ once: true, margin: '-50px' }}
      variants={{
        visible: {
          transition: {
            staggerChildren: 0.08,
            delayChildren: delay,
          },
        },
      }}
    >
      {words.map((word, index) => (
        <motion.span
          key={`${word}-${index}`}
          className='mr-2 inline-block'
          variants={{
            hidden: { opacity: 0, y: 50, rotateX: 90 },
            visible: {
              opacity: 1,
              y: 0,
              rotateX: 0,
              transition: {
                duration,
                ease: [0.25, 0.46, 0.45, 0.94],
              },
            },
          }}
        >
          {word}
        </motion.span>
      ))}
    </motion.div>
  );
}
