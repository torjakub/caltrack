import { useEffect, useState } from "react";
import NetInfo from "@react-native-community/netinfo";

export function useIsOnline(): boolean {
  const [isOnline, setIsOnline] = useState(true);

  useEffect(() => {
    return NetInfo.addEventListener((state) => {
      setIsOnline(!!state.isConnected && state.isInternetReachable !== false);
    });
  }, []);

  return isOnline;
}
