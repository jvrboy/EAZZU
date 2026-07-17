"""
Command Handler Module
Handles individual CLI commands
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime


class CommandHandler:
    """
    Command Handler
    Processes and executes CLI commands
    """

    def __init__(self, bot):
        self.bot = bot
        self.command_history: List[str] = []

    async def execute(self, command: str) -> Dict[str, Any]:
        """
        Execute a command and return result
        """
        self.command_history.append(command)

        parts = command.strip().split()
        if not parts:
            return {'success': False, 'message': 'Empty command'}

        cmd = parts[0].lower()
        args = parts[1:]

        result = {'success': True, 'command': cmd}

        try:
            if cmd == 'start':
                result['data'] = await self._start(args)
            elif cmd == 'stop':
                result['data'] = self._stop()
            elif cmd == 'pause':
                result['data'] = self._pause()
            elif cmd == 'resume':
                result['data'] = self._resume()
            elif cmd == 'stats':
                result['data'] = self._stats()
            elif cmd == 'trades':
                result['data'] = self._trades(args)
            elif cmd == 'indicators':
                result['data'] = self._indicators()
            elif cmd == 'config':
                result['data'] = self._config()
            else:
                result['success'] = False
                result['message'] = f"Unknown command: {cmd}"

        except Exception as e:
            result['success'] = False
            result['message'] = str(e)

        return result

    async def _start(self, args: List[str]) -> Dict[str, Any]:
        """Start the bot"""
        use_live = 'live' in args
        success = await self.bot.start(use_simulation=not use_live)
        return {
            'started': success,
            'mode': 'live' if use_live else 'simulation'
        }

    def _stop(self) -> Dict[str, Any]:
        """Stop the bot"""
        asyncio.create_task(self.bot.stop())
        return {'stopped': True}

    def _pause(self) -> Dict[str, Any]:
        """Pause trading"""
        asyncio.create_task(self.bot.pause())
        return {'paused': True}

    def _resume(self) -> Dict[str, Any]:
        """Resume trading"""
        asyncio.create_task(self.bot.resume())
        return {'resumed': True}

    def _stats(self) -> Dict[str, Any]:
        """Get statistics"""
        return self.bot.get_stats()

    def _trades(self, args: List[str]) -> Dict[str, Any]:
        """Get recent trades"""
        count = int(args[0]) if args and args[0].isdigit() else 10
        trades = self.bot.get_recent_trades(count)
        return {
            'count': len(trades),
            'trades': trades
        }

    def _indicators(self) -> Dict[str, Any]:
        """Get indicator status"""
        return self.bot.get_indicators_status()

    def _config(self) -> Dict[str, Any]:
        """Get configuration"""
        return self.bot.config.to_dict()
