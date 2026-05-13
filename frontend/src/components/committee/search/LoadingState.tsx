
import { Loader2 } from "lucide-react";

const LoadingState = () => {
  return (
    <div className="flex justify-center items-center h-64 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 rounded-3xl border border-blue-100/50 shadow-2xl backdrop-blur-sm">
      <div className="flex flex-col items-center space-y-6">
        <div className="relative">
          <div className="absolute inset-0 h-16 w-16 animate-ping rounded-full bg-gradient-to-r from-blue-400 to-purple-500 opacity-20"></div>
          <div className="absolute inset-2 h-12 w-12 animate-pulse rounded-full bg-gradient-to-r from-blue-500 to-purple-600 opacity-30"></div>
          <Loader2 className="relative h-16 w-16 animate-spin text-transparent bg-gradient-to-r from-blue-600 to-purple-700 bg-clip-text" />
          <div className="absolute inset-4 h-8 w-8 rounded-full bg-gradient-to-r from-white to-blue-50 shadow-lg"></div>
        </div>
        <div className="text-center space-y-2">
          <p className="text-gray-800 font-bold text-lg">Loading committees...</p>
          <p className="text-gray-600 text-sm">Preparing your workspace</p>
        </div>
      </div>
    </div>
  );
};

export default LoadingState;
