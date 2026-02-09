import { useState, useEffect } from 'react';

export const useTestReport = () => {
  const [testReport, setTestReport] = useState(null);

  useEffect(() => {
    const fetchTestReport = async () => {
      try {
        const response = await fetch('/api/test-report');
        const data = await response.json();
        setTestReport(data);
      } catch (error) {
        console.error('Failed to fetch test report:', error);
      }
    };

    fetchTestReport();
  }, []);

  return testReport;
};