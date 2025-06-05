'use client';

import { motion } from 'framer-motion';
import { Check, Clock, AlertCircle } from 'lucide-react';
import { GenerationStep } from '../hooks/useArticleGeneration';

interface GenerationStepsProps {
  steps: GenerationStep[];
  currentStep: string;
}

export default function GenerationSteps({ steps, currentStep }: GenerationStepsProps) {
  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="space-y-4">
        {steps.map((step, index) => (
          <motion.div
            key={step.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`flex items-center p-4 rounded-lg border transition-all duration-300 ${
              step.status === 'completed' 
                ? 'border-green-200 bg-green-50' 
                : step.status === 'in_progress'
                ? 'border-blue-200 bg-blue-50'
                : step.status === 'error'
                ? 'border-red-200 bg-red-50'
                : 'border-gray-200 bg-gray-50'
            }`}
          >
            <div className="flex-shrink-0 mr-4">
              {step.status === 'completed' ? (
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center"
                >
                  <Check className="w-5 h-5 text-white" />
                </motion.div>
              ) : step.status === 'in_progress' ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center"
                >
                  <Clock className="w-5 h-5 text-white" />
                </motion.div>
              ) : step.status === 'error' ? (
                <div className="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center">
                  <AlertCircle className="w-5 h-5 text-white" />
                </div>
              ) : (
                <div className="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                  <span className="text-sm font-semibold text-gray-600">{index + 1}</span>
                </div>
              )}
            </div>
            
            <div className="flex-1">
              <h3 className={`font-medium ${
                step.status === 'completed' ? 'text-green-800' :
                step.status === 'in_progress' ? 'text-blue-800' :
                step.status === 'error' ? 'text-red-800' :
                'text-gray-600'
              }`}>
                {step.title}
              </h3>
              {step.message && (
                <p className="text-sm text-gray-600 mt-1">{step.message}</p>
              )}
            </div>
            
            {step.status === 'in_progress' && (
              <motion.div
                className="flex-shrink-0 ml-4"
                animate={{ opacity: [0.5, 1, 0.5] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              >
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
              </motion.div>
            )}
          </motion.div>
        ))}
      </div>
    </div>
  );
}